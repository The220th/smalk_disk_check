# coding: utf-8

import re
from ksupk import is_int
from typing import Callable
import subprocess
import traceback
from pathlib import Path
from ksupk import singleton_decorator

from smalk_disk_check.setting_manager import SettingManager
from smalk_disk_check.smart_handler import SMARTHandler
from smalk_disk_check.mdadm_handler import MDADMHandler
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

    def remove_non_english_characters(input_string) -> str:
        return re.sub(r'[^a-zA-Z]', '', input_string)

    lsblk_list = []
    for line in lines[1:]:
        parts = line.split()
        name = remove_non_english_characters(parts[0])
        lsblk_list.append({
            "NAME": name,
            "UUID": parts[1] if len(parts) > 1 else None,
            # 'LABEL': parts[2] if len(parts) > 2 else None
        })

    return lsblk_list


class Disk:
    def __init__(self, name: str, code: str, dev_path: Path, disk_type: str, max_temp: int | None,
                 smart_attr_to_check: dict[int | str: Callable[[int], bool] | str]):
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

    def check(self) -> tuple[bool, str]:
        """

        :return: check_success, problem_text
        """
        if not self.check_if_in_system():
            return False, f"No such file: \"{self.get_dev_path()}\". "
        if not self.try_read():
            return False, f"Cannot read device \"{self.get_dev_path()}\". "
        problem, res = False, ""
        if self.get_max_temp() is not None and not self.is_mdadm():
            t = self.get_temp()
            if t is None:
                problem = True
                res += f"Cannot get temperature of device \"{self.get_dev_path()}\". \n"
            if t is not None and t > self.get_max_temp():
                problem = True
                res += f"Temperature of disk is too high: t={t}°C > max={self.get_max_temp()}°C. \n"
        if not self.is_mdadm():
            smart_table = self.get_smart_table()
            if smart_table is None:
                problem = True
                res += f"Cannot get S.M.A.R.T. from device \"{self.get_dev_path()}\". \n"
            try:
                f, o = self.check_smart_attributes(smart_table)
                if not f:
                    problem = True
                    res += f"Problem with S.M.A.R.T.: \n{o} \n"
                    res += f"smartctl -a {self.get_dev_path()}: \n {SMARTHandler.get_smart_a_of(self.get_dev_path(), self.get_disk_type())} \n"
            except Exception as e:
                problem = True
                res += f"Error while checking S.M.A.R.T.: {e}. \n"
        else:
            mdadm_check_f, mdadm_check_m = MDADMHandler.check_detail(self.get_dev_path())
            if not mdadm_check_f:
                problem = True
                res += f"Problem with RAID: \n {mdadm_check_m} \n"
                res += f"mdadm full report: \n {MDADMHandler.get_full_report(self.get_dev_path())} \n"

        if problem:
            res = f"{str(self)} \n" + res

        return not problem, res

    def get_report(self) -> str:
        res = ""
        if not self.check_if_in_system():
            res += f"No such file: \"{self.get_dev_path()}\". \n"
        if not self.try_read():
            res +=  f"Cannot read device \"{self.get_dev_path()}\". \n"

        if self.get_max_temp() is not None and not self.is_mdadm():
            t = self.get_temp()
            if t is None:
                res += f"Cannot get temperature of device \"{self.get_dev_path()}\". \n"
            else:
                res += f"Temperature of {self.get_dev_path()} is {t}°C (max={self.get_max_temp()}°C). \n"
            if t is not None and t > self.get_max_temp():
                res += f"Temperature of disk is too high: t={t}°C > max={self.get_max_temp()}°C. \n"

        if not self.is_mdadm():
            res += f"\n\nsmartctl -a {self.get_dev_path()}: \n {SMARTHandler.get_smart_a_of(self.get_dev_path(), self.get_disk_type())} \n"
            buffs, _smart_table = "", self.get_smart_table()
            if _smart_table is not None:
                for attr, val in _smart_table:
                    buffs += f"{attr} --- {val}\n"
            else:
                buffs = f"{_smart_table}"
            res += f"smart table: \n{buffs} \n"
        else:
            res += f"\n\nmdadm full report: \n {MDADMHandler.get_full_report(self.get_dev_path())} \n"

        return res

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
            if len(smart_table) == 0:
                raise RuntimeError(f"(Disk.get_smart_table) smart table has len zero. S.M.A.R.T. is \"{smart_table}\"")
            else:
                return smart_table
        except Exception as e:
            error_text = f"{traceback.format_exc()}\n{e}"
            print(error_text)
            return None

    def check_smart_attributes(self, smart_table: dict[int: int]) -> tuple[bool, str]:
        # try:
        #     smart_table: dict[int: int] = SMARTHandler.get_smart_table(self.get_dev_path(), self.get_disk_type())
        # except Exception as e:
        #     return False, "Cannot get S.M.A.R.T."

        res_str = ""
        for attr_num in self.smart_attr_to_check:
            if isinstance(attr_num, int):
                pass
            elif isinstance(attr_num, str):
                continue
            else:
                raise ValueError(f"(Disk.check_smart_attributes) attr_num \"{attr_num}\" must be only int or str, not {type(attr_num)}")
            if attr_num not in smart_table:
                raise RuntimeError(f"Cannot find attribute {attr_num} in S.M.A.R.T. ")
            value = smart_table[attr_num]
            lambda_f = self.smart_attr_to_check[attr_num]
            lambda_f_str = self.smart_attr_to_check[str(attr_num)]
            if lambda_f(value):
                res_str += f"S.M.A.R.T. is not passed. Attribute {attr_num} check fail. Attribute {attr_num} is \"{value}\", but problem if: \"{lambda_f_str}\". \n"

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

    def __str__(self):
        smart_attr_to_check = {}
        for k_i in self.smart_attr_to_check:
            if isinstance(k_i, str):
                smart_attr_to_check[k_i] = smart_attr_to_check[k_i]
            else:
                continue
        return (f"Disk(name={self.name}, code={self.code}, dev_path={self.dev_path}), disk_type={self.disk_type}, is_mdadm={self.mdadm}, "
                f"max_temp={self.max_temp}, smart_attr_to_check={smart_attr_to_check})")


@singleton_decorator
class DiskManager:

    def __init__(self, sm: SettingManager):
        disks = sm.get_disks()
        self.disks: list[Disk] = []

        dev_paths = []
        for disk_i in disks:
            self._check_corrent_of(disk_i)
            disk_name = disk_i["name"]
            disk_code = disk_i["code"]
            if disk_i["define_type"] == "dev":
                dev_path = self._check_define_dev(disk_i["disk"], disk_name)
            elif disk_i["define_type"] == "by-id":
                dev_path = self._check_define_by_id(disk_i["disk"], disk_name)
            elif disk_i["define_type"] == "uuid":
                dev_path = self._find_disk_by_uuid(disk_i["disk"], disk_name)
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
            smart_attr_to_check: dict[int | str: Callable[[int], bool] | str] = {}
            for smart_i in smarts:
                attr_num: int = int(smart_i["attribute_num"])
                condition: str = smart_i["problem_if"]
                smart_attr_to_check[attr_num] = eval(f"lambda x: {condition}")
                smart_attr_to_check[str(attr_num)] = condition
            disk = Disk(name=disk_name, code=disk_code, dev_path=dev_path, disk_type=disk_type, max_temp=max_temp,
                        smart_attr_to_check=smart_attr_to_check)
            self.disks.append(disk)

        for string in dev_paths:
            if dev_paths.count(string) > 1:
                raise ValueError(f"Several repetitions of the device \"{string}\"")

    def _check_corrent_of(self, disk_record: dict):
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

    def _check_define_dev(self, path: str, disk_name: str) -> Path:
        # pattern = r'^/dev/sd[a-z]$'  # nvme? mdX? scsi?
        pattern = r'^/dev/[a-zA-Z0-9]+$'
        if not re.match(pattern, path):
            raise ValueError(f"Cannot understand this: \"{path}\" -- of disk {disk_name}. ")
        res = Path(path)
        if res.exists():
            return res
        else:
            raise ValueError(f"File \"{str(res)}\" does not exist. ")

    def _check_define_by_id(self, path: str, disk_name: str) -> Path:
        pattern = r'^/dev/disk/by-id/[a-zA-Z0-9_-]+$'
        if not re.match(pattern, path):
            raise ValueError(f"Cannot understand this: \"{path}\" -- of disk {disk_name}. ")

        res = Path(path)
        if res.exists():
            if res.is_symlink():
                return res.resolve()
            else:
                return res
        else:
            raise ValueError(f"File \"{str(res)}\" does not exist. ")

    def _find_disk_by_uuid(self, uuid: str, disk_name: str) -> Path:
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
