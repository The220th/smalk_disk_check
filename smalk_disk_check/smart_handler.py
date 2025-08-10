# coding: utf-8

from pathlib import Path
import subprocess
from pySMART import Device

class SMARTHandler:

    @staticmethod
    def get_smart_table(dev: str | Path, dev_type: str | None) -> dict[int: int]:
        dev = str(dev)
        if dev_type is not None:
            smart = Device(dev)
        else:
            smart = Device(dev, interface=dev_type)

        smart_attributes = smart.attributes

        smart_dict: dict[int: int] = {}

        for attribute in smart_attributes:
            # smart_dict[attribute.num] = str(attribute.raw)
            smart_dict[attribute.num] = attribute.raw_int

        return smart_dict

    @staticmethod
    def try_get_temperature(dev: str | Path, dev_type: str | None) -> int | None:
        dev = str(dev)
        try:
            if dev_type is not None:
                smart = Device(dev)
            else:
                smart = Device(dev, interface=dev_type)

            res = smart.temperature
            return res
        except Exception as e:
            return None

    @staticmethod
    def get_smart_a_of(dev: str | Path, dev_type: str | None) -> str:
        dev = str(dev)
        if dev_type is not None:
            cmd = ["smartctl", "-a", "-d", dev_type, dev]
        else:
            cmd = ["smartctl", "-a", dev]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Cannot run cmd {cmd}: {e.stderr}")

    @staticmethod
    def get_smart_x_of(dev: str | Path, dev_type: str | None) -> str:
        dev = str(dev)
        if dev_type is not None:
            cmd = ["smartctl", "-x", "-d", dev_type, dev]
        else:
            cmd = ["smartctl", "-x", dev]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Cannot run cmd {cmd}: {e.stderr}")
