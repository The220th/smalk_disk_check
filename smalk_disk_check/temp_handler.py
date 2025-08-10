# coding: utf-8

from pathlib import Path
import subprocess
import time

class TempHandler:

    @staticmethod
    def get_temp(dev: str | Path) -> int | None:
        dev = str(dev)
        try:
            result = subprocess.run(["hddtemp", dev], capture_output=True, text=True, check=True)
            output = result.stdout.strip()

            if "is sleeping" in output:
                with open(dev, 'rb') as f:
                    f.read(1024)

                time.sleep(2)

                result = subprocess.run(["hddtemp", dev], capture_output=True, text=True, check=True)
                output = result.stdout.strip()

            temp_line = output.split(':')[-1].strip()
            temperature = temp_line.split()[0]
            return int(temperature)

        except subprocess.CalledProcessError:
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None
