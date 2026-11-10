# rts_covers

An interface between RTS covers and the web (RESTful API) using an Arduino and Python.

## Installation

In a Proxmox container, do not forget to configure the network interface. Also the sudo command is unknown, so you must manually run the command using sudo in the install file. It is also needed to install `usbutils` (to use `lsusb` in the container) and to passthrough the USB device you need to follow these instructions: https://gist.github.com/Vincent-Stragier/599758ba2b6ce30d0f5cf047f9f0d018.

```bash
sudo apt-get update && sudo apt-get install git
git clone https://github.com/Vincent-Stragier/rts_covers.git
cd rts_covers/
chmod +x install.sh & chmod 777 install.sh
sudo sh ./install.sh
```

### Alpine Linux (OpenRC)

On Alpine, the same `install.sh` is used (POSIX `sh`, no bash/systemd needed; it detects Alpine automatically):

```sh
apk add git
git clone https://github.com/Vincent-Stragier/rts_covers.git
cd rts_covers/
sh ./install.sh
```

It installs the packages with `apk`, creates the virtualenv (without `systemd-python`), and installs `/etc/init.d/rts_covers` (from `rts_covers.openrc`), enabled at the `default` runlevel. The service runs `routine.py --foreground` under `supervise-daemon`; logs go to `/var/log/rts_covers.log`, `/var/log/rts_covers.err` and syslog. Manage it with `rc-service rts_covers start|stop|restart|status`.

After the installation you must edit `settings.json` :

```json
{
    "Test": {
        "debug_messages": true, <-- not used?
        "context_mocking": false, <-- mock the daemon context
        --> used to debug routine.py (entry point of the project)
        "remote_mocking": false, <-- mock the remote for testing
        "time_mocking": false, <-- increase the time speed
    },
    "HTTP": { <-- configuration of the TCP server
        "enable": true,
        "port": 4242
    },
    "UART": { <-- configure the USB connection
        "VID_SR": "USB VID:PID=0000: 0000 SER: 12345678901234567890",
        "SPEED": 115200
    },
    "shutters": { <-- configure your shutters
        "shutter 0": {
            "id": "0x000001"
        },
        "shutter 1": {
            "id": "0x000002"
        }
    },
    "counters_path": "./counters" <-- path to the counters
}
```

To find the USB VID_SR, you can use the following command:

```bash
python3 -c 'import serial.tools.list_ports; print([f"{port}: {desc} [{hwid}]" for port, desc, hwid in sorted(serial.tools.list_ports.comports())])'
```

### HTTP server (API)

This server helps to interact with the shutters and the Arduino pins.

#### Interact with the shutters

```bash
http://hostname:port/?name=<a_name>&action=<valid_action>
```

#### Interact with the pins

```bash
http://hostname:port/?pin=<pin_number>&delay=<delay_in_ms>
```

## Usage in an unprivileged Proxmox container

The Arduino must be passed through to the container, and the container's user must be allowed to open it. Do this **only for the container that needs it**, and avoid handing the device to the default container root (host UID 100000): that UID is root in *every* unprivileged container using the default id mapping, so any container later given the device node would get full access to it.

Run the following on the Proxmox **host** (replace `114` with your container ID).

### Recommended: Proxmox device passthrough (Proxmox VE 8.1+)

```bash
pct set 114 -dev0 /dev/ttyACM0,gid=20,mode=0660
```

This makes the device available to this container only, owned by the group `20` (`dialout`, on Debian and Alpine) with mode `0660`, so no `chown` or cron job is needed. Add the user that runs the service to the `dialout` group inside the container (the default service runs as root, which does not need it).

### Stable device name (optional)

`/dev/ttyACM0` can change when other USB devices are plugged in. Match the Arduino by its serial number with a udev rule on the host (`/etc/udev/rules.d/99-rts-covers.rules`):

```text
SUBSYSTEM=="tty", ATTRS{idVendor}=="2341", ATTRS{idProduct}=="0043", ATTRS{serial}=="<your serial>", SYMLINK+="ttyRTS"
```

Then reload the rules (`udevadm control --reload && udevadm trigger`) and pass `/dev/ttyRTS` instead of `/dev/ttyACM0` in the `pct set` command. Use `udevadm info -a /dev/ttyACM0` to read the attributes.

### Older Proxmox versions

Follow the [passthrough gist](https://gist.github.com/Vincent-Stragier/599758ba2b6ce30d0f5cf047f9f0d018), and prefer a dedicated group or a custom idmap for the container over `chown 100000:...` plus a cron job.

### Checking from inside the container

```bash
ls -l /dev/ttyACM*
.venv/bin/python -c 'import serial.tools.list_ports as p; print([(x.device, x.hwid) for x in p.comports()])'
```

The `VID_SR` value in `settings.json` must be contained in the reported `hwid`.
