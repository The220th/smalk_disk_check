# coding: utf-8

import re
from ksupk import is_int
from typing import Callable
import subprocess
from pathlib import Path
from ksupk import singleton_decorator

from smalk_disk_check.setting_manager import SettingManager
from smalk_disk_check.smart_handler import SMARTHandler
from smalk_disk_check.temp_handler import TempHandler


def is_valid_attribute_check_condition(condition: str) -> bool:
    pattern1 = r"^x\s*(>=|<=|==|>|<|=|!=)\s*-?\d+$"
    pattern2 = r"^-?\d+\s*(>=|<=|==|>|<|=|!=)\s*x$"
    return (re.match(pattern1, condition.replace(" ", "")) is not None or
            re.match(pattern2, condition.replace(" ", "")) is not None)


def get_lsblk_info() -> list[dict[str: str]]:
    try:
        result = subprocess.run(['lsblk', '-o', 'NAME,UUID,LABEL'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error of running \"lsblk -o NAME,UUID\": {e}")

    lsblk_list = []
    for line in lines[1:]:
        parts = line.split()
        lsblk_list.append({
            "NAME": parts[0],
            "UUID": parts[1] if len(parts) > 1 else None,
            # 'LABEL': parts[2] if len(parts) > 2 else None
        })

    return lsblk_list


class Disk:
    def __init__(self, name: str, code: str, dev_path: Path, disk_type: str, max_temp: int | None,
                 smart_attr_to_check: dict[int: Callable[[int], bool]]):
        self.name: str = name
        self.code: str = code
        self.dev_path: Path = dev_path

        disk_type = disk_type.strip().lower()
        if disk_type == "mdadm":
            self.mdadm: bool = True
        else:
            self.mdadm: bool = False
        self.disk_type: str = disk_type

        self.max_temp: int | None = max_temp
        self.smart_attr_to_check = smart_attr_to_check

    def get_name(self) -> str:
        return self.name

    def get_code(self) -> str:
        return self.code

    def get_temp(self) -> int | None:
        tmp1 = TempHandler.get_temp(self.get_dev_path())
        if tmp1 is None:
            tmp2 = SMARTHandler.try_get_temperature(self.get_dev_path(), self.get_disk_type())
            # assert tmp1 == tmp2
            return tmp2
        else:
            return tmp1

    def try_read(self) -> bool:
        try:
            with open(self.get_dev_path(), 'rb') as f:
                f.read(1024)
            return True
        except Exception as e:
            return False

    def check_if_in_system(self) -> bool:
        if Path(self.get_dev_path()).exists():
            return self.try_read()
        else:
            return False

    def get_smart_table(self) -> dict[int: int] | None:
        try:
            smart_table: dict[int: int] = SMARTHandler.get_smart_table(self.get_dev_path(), self.get_disk_type())
            return smart_table
        except Exception as e:
            return None

    def check_smart_attributes(self, smart_table: dict[int: int]) -> tuple[bool, str]:
        # try:
        #     smart_table: dict[int: int] = SMARTHandler.get_smart_table(self.get_dev_path(), self.get_disk_type())
        # except Exception as e:
        #     return False, "Cannot get S.M.A.R.T."

        res_str = ""
        for attr_num in self.smart_attr_to_check:
            if attr_num not in smart_table:
                raise RuntimeError(f"Cannot find attribute {attr_num} in S.M.A.R.T.")
            value = smart_table[attr_num]
            if not self.smart_attr_to_check[attr_num](value):
                res_str += f"S.M.A.R.T. is not passed. Attribute {attr_num} check fail. Attribute {attr_num} is \"{smart_table[attr_num]}\". "

        if res_str == "":
            return True, res_str
        else:
            return False, res_str

    def get_max_temp(self) -> int | None:
        return self.max_temp

    def get_dev_path(self) -> Path:
        return Path(self.dev_path)

    def get_disk_type(self) -> str:
        return self.disk_type

    def is_mdadm(self) -> bool:
        return self.mdadm


@singleton_decorator
class DiskManager:

    def __init__(self, sm: SettingManager):
        disks = sm.get_disks()
        self.disks: list[Disk] = []

        dev_paths = []
        for disk_i in disks:
            DiskManager._check_corrent_of(disk_i)
            disk_name = disk_i["name"]
            disk_code = disk_i["code"]
            if disk_i["define_type"] == "dev":
                dev_path = DiskManager._check_define_dev(disk_i["disk"], disk_name)
            elif disk_i["define_type"] == "by-id":
                dev_path = DiskManager._check_define_by_id(disk_i["disk"], disk_name)
            elif disk_i["define_type"] == "uuid":
                dev_path = DiskManager._find_disk_by_uuid(disk_i["disk"], disk_name)
            else:
                raise ValueError(f"(DiskManager.__init__) Failed successfully.")
            dev_paths.append(dev_path)

            disk_type = disk_i["type"]

            if is_int(disk_i["max_temp"]):
                max_temp = int(disk_i["max_temp"])
            elif str(disk_i["max_temp"]).strip().lower() == "none":
                max_temp = None
            else:
                raise ValueError(f"Cannot understand \"max_temp\"=\"{disk_i['max_temp']}\" of disk {disk_name}")

            smarts = disk_i["smart_check"]
            smart_attr_to_check: dict[int: Callable[[int], bool]] = {}
            for smart_i in smarts:
                attr_num: int = int(smart_i["attribute_num"])
                condition: str = smart_i["problem_if"]
                smart_attr_to_check[attr_num] = eval(f"lambda x: {condition}")
            disk = Disk(name=disk_name, code=disk_code, dev_path=dev_path, disk_type=disk_type, max_temp=max_temp,
                        smart_attr_to_check=smart_attr_to_check)
            self.disks.append(disk)

        for string in dev_paths:
            if dev_paths.count(string) > 1:
                raise ValueError(f"Several repetitions of the device \"{string}\"")

    @staticmethod
    def _check_corrent_of(disk_record: dict):
        if "name" not in disk_record:
            raise ValueError(f"\"name\" not defined for disk. ")
        name = disk_record["name"]
        if "code" not in disk_record:
            raise ValueError(f"\"code\" not defined for disk. Make it the same as the \"name\" if you do not know why it is needed. ")
        code = disk_record["code"]
        if "define_type" not in disk_record:
            raise ValueError(f"\"define_type\" not defined for disk \"{name}\" ({code}). ")
        allowed_define_types = ["dev", "by-id", "uuid"]
        if disk_record["define_type"] not in allowed_define_types:
            raise ValueError(f"\"define_type\" must be only: {allowed_define_types}, not \"{disk_record['define_type']}\"")
        if "disk" not in disk_record:
            raise ValueError(f"\"disk\" not defined for disk \"{name}\" ({code}). ")
        if "type" not in disk_record:
            raise ValueError(f"\"type\" not defined for disk \"{name}\" ({code}). ")
        if "max_temp" not in disk_record:
            raise ValueError(f"\"max_temp\" not defined for disk \"{name}\" ({code}). ")
        if "smart_check" not in disk_record:
            raise ValueError(f"\"smart_check\" not defined for disk \"{name}\" ({code}). ")
        smarts = disk_record["smart_check"]
        for smart_i in smarts:
            if "attribute_num" not in smart_i:
                raise ValueError(f"\"attribute_num\" not defined: {smart_i}. Disk \"{name}\" ({code}). ")
            if not isinstance(smart_i["attribute_num"], int):
                raise ValueError(f"\"attribute_num\" must be int, not {type(smart_i['attribute_num'])}. Disk \"{name}\" ({code}). ")
            if "problem_if" not in smart_i:
                raise ValueError(f"\"problem_if\" not defined: {smart_i}. Disk \"{name}\" ({code}). ")
            if not isinstance(smart_i["problem_if"], str):
                raise ValueError(f"\"problem_if\" must be int, not {type(smart_i['problem_if'])}. Disk \"{name}\" ({code}). ")
            if not is_valid_attribute_check_condition(smart_i["problem_if"]):
                raise ValueError(f"\"problem_if\" contains wrong condition: \"{smart_i['problem_if']}\". Disk \"{name}\" ({code}). ")

    @staticmethod
    def _check_define_dev(path: str, disk_name: str) -> Path:
        # pattern = r'^/dev/sd[a-z]$'  # nvme? mdX? scsi?
        pattern = r'^/dev/[a-zA-Z0-9]+$'
        if not re.match(pattern, path):
            raise ValueError(f"Cannot understand this: \"{path}\" -- of disk {disk_name}. ")
        res = Path(path)
        if res.exists():
            return res
        else:
            raise ValueError(f"File \"{str(res)}\" does not exist. ")

    @staticmethod
    def _check_define_by_id(path: str, disk_name: str) -> Path:
        pattern = r'^/dev/disk/by-id/[a-zA-Z0-9_-]+$'
        if not re.match(pattern, path):
            raise ValueError(f"Cannot understand this: \"{path}\" -- of disk {disk_name}. ")

        res = Path(path)
        if res.exists():
            return res
        else:
            raise ValueError(f"File \"{str(res)}\" does not exist. ")

    @staticmethod
    def _find_disk_by_uuid(uuid: str, disk_name: str) -> Path:
        uuid = uuid.strip().lower()
        lsblk: list[dict[str: str]] = get_lsblk_info()

        disks = []
        for record in lsblk:
            name, disk_uuid = str(record["NAME"]), str(record["UUID"])
            if disk_uuid.strip().lower() == uuid:
                disks.append(f"/dev/{name}")

        if len(disks) == 0:
            raise ValueError(f"Cannot find disk, where volume \"{uuid}\" exists. ")
        elif len(disks) > 1:
            raise ValueError(f"Multiple disks with the specified UUID (\"{uuid}\") were found. Disk \"{disk_name}\"")
        else:
            res = Path(disks[0])

        return res

    def get_disks(self) -> list[Disk]:
        return self.disks
