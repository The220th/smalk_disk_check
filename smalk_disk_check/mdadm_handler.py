# coding: utf-8

import re
import os
from pathlib import Path
import subprocess


class MDADMHandler:

    @staticmethod
    def check_detail(dev: str | Path) -> tuple[bool, str]:
        dev = str(dev)

        try:
            result = subprocess.run(
                ["mdadm", "--detail", dev],
                capture_output=True,
                text=True,
                check=True
            )
            output = result.stdout

            """
            Основные возможные состояния (State):
                clean – OK.
                active – OK.
                degraded – work, but there are failed disks.
                resyncing – sync.
                recovering – recover.
                reshape – change raid, or size, or number of disks.
                checking – check raid consistency.
                faulty – fail.
                inactive – stopped.
            """
            if "State :" in output and "Failed Devices :" in output:
                state_line = [line for line in output.split('\n') if "State :" in line]
                fail_line = [line for line in output.split('\n') if "Failed Devices :" in line]
                if len(state_line) != 1 or len(fail_line) != 1:
                    return False, f"Cannot understand state of \"{dev}\""
                state_line, fail_line = state_line[0], fail_line[0]
                state = state_line.split(":")[1].strip().lower()
                fails_num = int(fail_line.split(":")[1].strip())
                res_text, all_ok = "", True
                if "faulty" in state or "inactive" in state or "degraded" in state:
                    res_text += f"Problem with RAID {dev}! State: {state}. \n"
                    all_ok = False
                if fails_num > 0:
                    res_text += f"Problem with RAID {dev}! Failed Devices: {fails_num}. \n"
                if all_ok:
                    return True, ""
                else:
                    return False, res_text
            else:
                return False, f"Cannot understand state of \"{dev}\""

        except subprocess.CalledProcessError as e:
            print(f"Error executing mdadm command: {e.stderr}")
            return False, "Error "
        except Exception as e:
            return False, f"Error: {e}"

    @staticmethod
    def get_full_report(dev: str | Path) -> str:
        dev = str(dev)
        res = ""
        output = None
        try:
            result = subprocess.run(
                ["mdadm", "--detail", dev],
                capture_output=True,
                text=True,
                check=True
            )
            output = result.stdout
        except Exception as e:
            res += f"Cannot run command \"mdadm --detail {dev}\": {e} \n"

        res += f"mdadm --detail {dev}: \n\n{output} \n"

        mdstat_content = None
        try:
            mdstat_content = open("/proc/mdstat", 'r').read()
        except Exception as e:
            res += f"Cannot read file /proc/mdstat: {e} \n"

        res += f"/proc/mdstat: \n\n{mdstat_content}"

        return res


if __name__ == "__main__":
    devdisk = "/dev/md0"
    o = MDADMHandler.get_full_report(devdisk)
    print(o, "\n\n\n")
    print(MDADMHandler.check_detail(devdisk))
    """
for i in {1..10}; do
    if [ ! -f "disk$i.img" ]; then
        dd if=/dev/zero of="disk$i.img" bs=1M count=1024
    fi
done

for i in {1..10}; do
    losetup -f "disk$i.img"
done

LOOPS=$(losetup -l | grep disk | awk '{print $1}')

mdadm --create --verbose /dev/md0 --level=6 --raid-devices=10 $LOOPS

cat /proc/mdstat
mdadm --detail /dev/md0
    """
