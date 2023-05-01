# rts_covers

An interface between RTS covers and the web (RESTful API) using an Arduino and Python.

## Installation

```bash
sudo apt-get update && sudo apt-get install git
git clone git:https://github.com/[...].git
cd motorised_blinds/
sudo bash ./install.sh
```

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

### HTTP server (API)

This server helps to interact with the shutters and the Arduino pins.

#### Interact with the shutters

```
http://hostname:port/?name=<a_name>&action=<valid_action>
```

#### Interact with the pins

```
http://hostname:port/?pin=<pin_number>&delay=<delay_in_ms>
```

## Usage in a unprivilaged container

My current installation is virtualised in a unprivilaged Proxmox container, however, for the access to the USB device, I need to change the ownership of the device file. To do so, I have added the following line to my crontab file (`crontab -e` to access the file in a terminal) in order to set the correct access right every 5 minutes:

```bash
*/5 * * * * /root/set_usb_access_right.sh
```

The `/root/set_usb_access_right.sh` simply contains the following:

```bash
chown 100000:100020 /dev/ttyACM0
```
