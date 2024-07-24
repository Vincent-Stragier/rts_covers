"""This module provides functions to generate Somfy RTS frames."""

import json
import os

# 0x1 | My | Stop or move to favourite position
# 0x2 | Up | Move up
# 0x3 | My + Up | Set upper motor limit in initial programming mode
# 0x4 | Down | Move down
# 0x5 | My + Down | Set lower motor limit in initial programming mode
# 0x6 | Up + Down | Change motor limit and initial programming mode
# 0x8 | Prog | Used for (de-)registering remotes, see below
# 0x9 | Sun + Flag | Enable sun and wind detector (SUN and FLAG symbol on
#       the Telis Soliris RC)
# 0xA | Flag | Disable sun detector (FLAG symbol on
#       the Telis Soliris RC)

# Sources:
#     https://pushstack.wordpress.com/somfy-rts-protocol/
#     http://www.automatedshadeinc.com/files/motors/
#     all-somfy-rts%20motors-programming-quick-guide-02-09.pdf

COMMANDS = {
    # My or Stop
    "MY": 0x01,
    "STOP": 0x01,
    # Up
    "UP": 0x02,
    "HAUT": 0x02,
    # My and up (set upper motor limit in initial programming mode)
    "MY_UP": 0x03,
    # Down
    "DOWN": 0x04,
    "BAS": 0x04,
    # My and down (set lower motor limit in initial programming mode)
    "MY_DOWN": 0x05,
    # Up and down (change motor limit and initial programming mode)
    "UP_DOWN": 0x06,
    # Prog ((de-)registering remotes)
    "PROG": 0x08,
    # Enable sun and wind detector
    # (SUN and FLAG symbol on the Telis Soliris RC)
    "SUN_FLAG": 0x09,
    # Disable sun detector (FLAG symbol on the Telis Soliris RC)
    "SUN_UNFLAG": 0x0A,
}


def str_to_int(string: str) -> int:
    """Try to convert a string to an int

    Args:
        string (str): the string to convert

    Returns:
        int: the converted string
    """
    string.replace(" ", "")
    if string.startswith("0x"):
        return int(string, 16)

    if string.startswith("0b"):
        return int(string, 2)

    return int(string, 10)


def read_config_file(path: str = "") -> any:
    """Read a json file and return its content"""
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def write_config_file(content: dict, path: str = "") -> None:
    """Write a json file with the given content"""
    with open(path, "w", encoding="utf-8") as file:
        json.dump(content, file, indent=4)


def save_counter(path: str = "", current_counter: int = 0) -> None:
    """Save a counter in a file"""
    try:
        os.makedirs(os.path.dirname(path))

    except FileExistsError:
        pass

    with open(path, "w+", encoding="utf-8") as file:
        file.write(str(current_counter % 2**16))


def read_counter(path: str = "") -> int:
    """Read a counter from a file"""
    try:
        with open(path, "r", encoding="utf-8") as file:
            return int(file.read())

    except ValueError:
        return -1


def frame_to_string(frame: bytearray) -> str:
    """Convert a frame to a string"""
    return " ".join([("0" + hex(byte)[2:])[-2:].upper() for byte in frame])


def print_frame(frame: bytearray) -> None:
    """Print a frame"""
    print(frame_to_string(frame))


def generate_somfy_base_frame(
    command, rolling_code_counter, remote_id
) -> list:
    """Generate a base frame for Somfy RTS protocol."""
    if isinstance(command, str):
        command = COMMANDS[command.upper()]

    if isinstance(rolling_code_counter, str):
        rolling_code_counter = str_to_int(rolling_code_counter)

    if isinstance(remote_id, str):
        remote_id = str_to_int(remote_id)

    rolling_code_counter = rolling_code_counter % 2**16
    remote_id = remote_id & 0xFFFFFF

    return [
        0xA7,
        command << 4 & 0xFF,
        rolling_code_counter >> 8 & 0xFF,
        rolling_code_counter & 0xFF,
        remote_id >> 16 & 0xFF,
        remote_id >> 8 & 0xFF,
        remote_id & 0xFF,
    ]


def generate_somfy_add_frame_checksum(frame: bytearray) -> bytearray:
    """Add the checksum to a frame."""
    # Calcul de la somme de vérification (checksum)
    # Compute checksum
    checksum = 0
    for byte in frame:
        checksum = checksum ^ byte ^ (byte >> 4)
    checksum &= 0b1111

    # Ajout de la checksum à la trame
    # Adds checksum to the frame
    frame[1] |= checksum
    return frame


def generate_somfy_obfuscate_frame(frame: bytearray) -> bytearray:
    """Obfuscate a frame."""
    # Obfuscation de la trame ("brouillage du sens de la trame")
    # Obfuscation of the frame ("encrypt the frame")

    for index in range(1, 7):
        frame[index] ^= frame[index - 1]

    return frame


def generate_somfy_full_frame(
    command, rolling_code_counter, remote_id
) -> list:
    """Generate a full frame for Somfy RTS protocol."""
    return generate_somfy_obfuscate_frame(
        generate_somfy_add_frame_checksum(
            generate_somfy_base_frame(command, rolling_code_counter, remote_id)
        )
    )


def counters_path(config_file_path):
    """Return the path to the counters directory"""
    _config = read_config_file(config_file_path)
    _counters_root = _config["counters_path"]

    if not os.path.isabs(_config["counters_path"]):
        _counters_root = os.path.join(
            os.path.dirname(config_file_path), _counters_root.replace("./", "")
        )

    return _counters_root


def shutter_id_and_counter(config_file_path, shutter_key) -> tuple:
    """Return the shutter id and counter"""
    _config = read_config_file(config_file_path)
    _counters_root = _config["counters_path"]

    if not os.path.isabs(_config["counters_path"]):
        _counters_root = os.path.join(
            os.path.dirname(config_file_path), _counters_root.replace("./", "")
        )

    _shutter_id = _config["shutters"][shutter_key]["id"]
    _counter_path = os.path.join(_counters_root, f"{_shutter_id}.txt")

    return int(_shutter_id, 16), read_counter(_counter_path)


def increment_shutter_counter(config_file_path, shutter_key):
    """Increment the shutter counter"""
    _config = read_config_file(config_file_path)
    _counters_root = _config["counters_path"]

    if not os.path.isabs(_config["counters_path"]):
        _counters_root = os.path.join(
            os.path.dirname(config_file_path), _counters_root.replace("./", "")
        )

    _shutter_id = _config["shutters"][shutter_key]["id"]
    _counter_path = os.path.join(_counters_root, f"{_shutter_id}.txt")
    save_counter(
        path=_counter_path,
        current_counter=read_counter(path=_counter_path) + 1,
    )


def decrement_shutter_counter(config_file_path, shutter_key):
    """Decrement the shutter counter"""
    _config = read_config_file(config_file_path)
    _counters_root = _config["counters_path"]
    if not os.path.isabs(_config["counters_path"]):
        _counters_root = os.path.join(
            os.path.dirname(config_file_path), _counters_root.replace("./", "")
        )
    _shutter_id = _config["shutters"][shutter_key]["id"]
    _counter_path = os.path.join(_counters_root, f"{_shutter_id}.txt")
    save_counter(
        path=_counter_path,
        current_counter=read_counter(path=_counter_path) - 1,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="shutter")
    args = parser.parse_args()

    print("Open config file...")
    config_file = os.path.abspath(args.config)
    config = read_config_file(config_file)

    counters_root = counters_path(config_file)

    # Read each counter value or create counter file
    for name, conf in config["shutters"].items():
        # int(conf["id"], 16)
        # print(conf["id"])
        counter_path = os.path.join(counters_root, f"{conf['id']}.txt")
        try:
            print(
                f"Counter value for {conf['id']}: {read_counter(counter_path)}"
            )
        except FileNotFoundError:
            print(f"Create counter file for {conf['id']}")
            save_counter(counter_path)

    shutter_id, counter = shutter_id_and_counter(
        config_file, "volet framboisiers"
    )
    current_frame = generate_somfy_full_frame(
        command=COMMANDS["UP"],
        rolling_code_counter=counter,
        remote_id=shutter_id,
    )
    print_frame(current_frame)

    success = True
    if success:
        increment_shutter_counter(config_file, "volet framboisiers")

    # current_frame = generate_somfy_base_frame(
    #     command=COMMANDS["UP"],
    #     rolling_code_counter=1284,
    #     remote_ID=int(shutter["id"], 16),
    # )
    # print_frame(current_frame)

    # current_frame = generate_somfy_add_frame_checksum(current_frame)
    # print_frame(current_frame)

    # current_frame = generate_somfy_obfuscate_frame(current_frame)
    # print_frame(current_frame)
