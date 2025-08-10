# coding: utf-8

import platform
import sys
import time

from smalk_disk_check.install_checking import install_check_and_root_check
from smalk_disk_check.args_parsing import get_args
from smalk_disk_check.setting_manager import SettingManager
from smalk_disk_check.disk import DiskManager


def main():
    while True:
        try:
            if platform.system().lower() != "linux":
                print("smalk_disk_check can run only on GNU/Linux.")
                sys.exit(1)
            install_check_and_root_check()

            args = get_args()
            sm = SettingManager(args.settings_path)
            disk_manager = DiskManager(sm)
        except Exception as e:
            print("Something gone wrong. Restarting...")
            time.sleep(5)


if __name__ == "__main__":
    main()
