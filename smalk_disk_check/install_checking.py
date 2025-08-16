# coding: utf-8

import subprocess
import os

def sys_check_program(program):
    # shutil.which ???
    try:
        subprocess.run([program, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except subprocess.CalledProcessError:
        print(f"WARNING: command \"{program} --version\" exited with error, but \"{program}\" installed. ")
        return True
    except FileNotFoundError:
        return False


def root_check() -> bool:
    if os.geteuid() == 0:
        return True
    else:
        return False


def install_check_and_root_check():
    if not root_check():
        print("This program must be run as root. ")
        exit()
    programs = {
        "lsblk": "util-linux",
        "mdadm": "mdadm",
        "smartctl": "smartmontools",
        "hddtemp": "hddtemp",
        "hdparm": "hdparm"
        # "sensors": "lm-sensors",
    }

    f = False
    for program, package in programs.items():
        if not sys_check_program(program):
            f = True
            print(f"\"{program}\" is not installed. Try to install it with package: \"{package}\". ")

    if f:
        print("Be sure, what all of these utils installed on your system: lsblk, mdadm, smartctl, hddtemp -- and rerun. ")
        print("The problem may also be related to the fact that these programs are not installed for the root user, but are installed for regular users.")
        exit()
