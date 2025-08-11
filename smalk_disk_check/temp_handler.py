# coding: utf-8

import re
from pathlib import Path
import subprocess
import time


class TempHandler:

    @staticmethod
    def get_temp(dev: str | Path) -> int | None:
        dev = str(dev)

        def run_hddtemp() -> str | None:
            try:
                result_l = subprocess.run(
                    ["hddtemp", dev],
                    capture_output=True,
                    text=True,
                    check=True
                )
                # print(result_l.stdout, " ::: ", result_l.stderr)
                return result_l.stdout.strip()
            except subprocess.CalledProcessError:
                return None

        def wake_disk() -> bool:
            try:
                subprocess.run(["hdparm", "-S0", dev], capture_output=True, text=True)
                subprocess.run(["hdparm", "-I", dev], capture_output=True, text=True)
                return True
            except Exception as e:
                print(f"Error while wake up with hdparm: {e}")
                return False

        try:
            output = run_hddtemp()

            if "is sleeping" in output.lower():  # sudo hdparm -Y /dev/sda
                # print(f"Device {dev} is sleeping. Trying to wake up... ")
                if wake_disk():
                    time.sleep(5)
                    output = run_hddtemp()
                    if not output:
                        return None
                else:
                    return None

            try:
                return int(output[output.rfind(": ")+2: output.rfind("°C")])  # : 33°C
            except Exception as e:
                return None
            # match = re.search(r'(\d+)\s*°?', output)
            # if match:
            #     try:
            #         return int(match.group(1))
            #     except ValueError:
            #         return None

        except Exception as e:
            print(f"Unexpected error: {e}")
            return None


if __name__ == "__main__":
    t = TempHandler.get_temp("/dev/sda")
    print(t)
