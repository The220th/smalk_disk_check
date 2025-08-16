# coding: utf-8

import yaml
from pathlib import Path
from ksupk import singleton_decorator


@singleton_decorator
class SettingManager:

    def __init__(self, settings_yaml_path: Path | str):
        settings_yaml_path = Path(settings_yaml_path)

        with open(settings_yaml_path, 'r', encoding="utf-8") as file:
            data = yaml.safe_load(file)

        self.data: dict = dict(data)

    def get_disks(self) -> list:
        return self.data["disk"]

    def get_my_keys(self) -> tuple[str, str, str, str]:
        return self.data["keys"]["priv_key"], self.data["keys"]["pub_key"], self.data["keys"]["sign_key"], self.data["keys"]["verify_key"]

    def get_alerk_keys(self) -> tuple[str, str]:
        return self.data["alerk"]["pub_key"], self.data["alerk"]["verify_key"]

    def get_sym_key(self) -> str:
        return self.data["app"]["cipher_key"]

    def get_alerk_conn(self) -> tuple[str, int, str]:
        return self.data["alerk"]["ip"], self.data["alerk"]["port"], self.data["alerk"]["endpoint"]

    def get_protocol(self) -> str:
        res: str = self.data["alerk"]["protocol"]
        if res.strip().lower() not in ["http", "https"]:
            raise ValueError("protocol must be only: \"http\" or \"https\"")
        return res

    def get_url(self) -> str:
        protocol = self.get_protocol().strip().lower()
        ip, port, endpoint = self.get_alerk_conn()
        return f"{protocol}://{ip}:{port}{endpoint}"

    def notify_if_turned_on(self) -> bool:
        return self.data["app"]["notify_if_turned_on"]

    def disk_polling_rate(self) -> int:
        return self.data["app"]["disk_polling_rate"]

    def full_report_period(self) -> int:
        return self.data["app"]["full_report_period"]

    def get_prefix_message(self) -> str:
        return self.data["app"]["prefix_message"]

    def get_startup_message(self) -> str:
        return self.data["app"]["startup_message"]

    def get_problem_message(self) -> str:
        return self.data["app"]["problem_message"]

    def get_full_report_message(self) -> str:
        return self.data["app"]["full_report_message"]
