# smalk_disk_check

[smalk](https://github.com/The220th/alerk?tab=readme-ov-file#writing-your-own-smalk) implementation for disk checking and monitoring.

> [!WARNING]
> This project has not been audited for security.

# Installation

Install packages:

```bash
sudo apt update && sudo apt install util-linux mdadm smartmontools hddtemp hdparm  # Debian-like
# or
sudo pacman -Sy util-linux mdadm smartmontools hddtemp hdparm  # Arch
```

Install form pip:

```bash
python3 -m pip install --upgrade pip
pip3 install smalk_disk_check
```

# Configuration and running

Copy `settings_template.yaml` as `settings.yaml`, change it as you need and run ([read more about keys](https://github.com/The220th/alerk)):

```bash
smalk_disk_check /path/to/settings.yaml
```

# Run it with startup

Create script `smalk_disk_check.sh` (as root):

```bash
#!/bin/bash
SCRIPT_DIR_PATH=$(dirname "$0")
VENV_PATH="$SCRIPT_DIR_PATH/venv"

if [ ! -d "$VENV_PATH" ]; then
    python3 -m venv "$VENV_PATH"

    . "$VENV_PATH/bin/activate"

    pip3 install --upgrade pip

    pip3 install smalk_disk_check
else
    . "$VENV_PATH/bin/activate"
fi

smalk_disk_check /path/to/settings.yaml
```

Then do it executable and set up crontab.

```bash
sudo chmod u+x /path/to/smalk_disk_check.sh

sudo crontab -e  # sudo pacman -S cronie or sudo apt install cronie 
                    # -> sudo systemctl start cronie && sudo systemctl enable cronie

# add to the end:
@reboot sleep 30 && /path/to/smalk_disk_check.sh
```

And reboot to test. Do not forget change `app.interactive` to `False` in `/path/to/settings.yaml`.

Or do it as systemd service.
