# coding: utf-8

import argparse
from smalk_disk_check import __version__


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="smalk_disk_check is smalk implementation for disk checking and monitoring. ")

    parser.add_argument("--version", action="version", version=f"V{__version__}", help="Check version. ")

    parser.add_argument("settings_path", type=str, help="Path to yaml file with settings. ")

    return parser.parse_args()
