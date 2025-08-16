# coding: utf-8

import platform
import sys
import time

from smalk_disk_check.install_checking import install_check_and_root_check
from smalk_disk_check.args_parsing import get_args
from smalk_disk_check.setting_manager import SettingManager
from smalk_disk_check.disk import DiskManager
from smalk_disk_check.key_manager import KeyManager
from smalk_disk_check.process import main_loop
from smalk_disk_check.communicator import Kommunicator


def main():
    if platform.system().lower() != "linux":
        print("smalk_disk_check can run only on GNU/Linux.")
        sys.exit(1)
    install_check_and_root_check()

    args = get_args()
    sm = SettingManager(args.settings_path)
    disk_manager = DiskManager(sm=sm)
    km = KeyManager(sm=sm)
    kommunicator = Kommunicator(url=sm.get_url(),
                                priv_key=km.get_priv_key(), public_key=km.get_pub_key(),
                                sign_key=km.get_sign_key(), verify_key=km.get_verify_key(),
                                alerk_pub_key=km.get_alerk_pub_key(), alerk_verify_key=km.get_alerk_verify_key(),
                                sym_key=km.get_sym_key())
    kommunicator.start()
    main_loop()


if __name__ == "__main__":
    main()
