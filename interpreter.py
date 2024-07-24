"""Interpret the commands from a json or a string."""

import re

from somfy_frame_generator import (
    frame_to_string,
    generate_somfy_full_frame,
    read_config_file,
    shutter_id_and_counter,
    str_to_int,
)


def decode_json_commands(settings: str, recipe: str):
    """Decode a recipe from a json file."""
    commands = []
    for shutter_command in read_config_file(settings)["Recipes"][recipe]:
        # Retrieve command, shutter counter and shutter's id.
        shutter_id, counter = shutter_id_and_counter(
            settings, shutter_command["shutter"]
        )
        commands.append(
            {
                "command": shutter_command["command"],
                "shutter": shutter_command["shutter"],
                "counter": counter,
                "shutter_id": shutter_id,
                "frame": frame_to_string(
                    generate_somfy_full_frame(
                        shutter_command["command"], counter, shutter_id
                    )
                ),
            }
        )
    return commands


def remove_command_name(command: str, command_base: str):
    """Remove the command name from the command."""
    return command[len(command_base) + 1 : -1]


def extract_arguments(arguments_str: str):
    """Extract the arguments from a string."""
    # Can fail ...
    regex = r"('[\w*,*\s*]+'|\"[\w*,*\s*]+\"|[0-9A-Fa-fxX]+)"
    matches = re.findall(regex, arguments_str, re.MULTILINE)

    arguments = []
    for match in matches:
        # string
        if match.startswith("'") and match.endswith("'"):
            arguments.append(match[1:-1])

        # string
        elif match.startswith('"') and match.endswith('"'):
            arguments.append(match[1:-1])

        # int (0b10, 0xF0, 90)
        else:
            arguments.append(str_to_int(match))

    return arguments


def decode_str_commands(settings: str, commands: str):
    """Decode a recipe from a string."""
    commands = commands.splitlines()

    decoded_commands = []
    for command in commands:
        if command.startswith("send(") and command.endswith(")"):
            command = remove_command_name(command, "send")
            arguments = extract_arguments(command)

            if len(arguments) not in (2, 3):
                raise ValueError(
                    "`send()` must contain 2 or 3 arguments.\n"
                    f"Received {command}"
                )

            shutter_id, counter = shutter_id_and_counter(
                settings, arguments[0]
            )

            if len(arguments) > 2:
                counter = arguments[2]

            frame = generate_somfy_full_frame(
                arguments[1], counter, shutter_id
            )

            decoded_commands.append(
                {
                    "command_base": "send",
                    "arguments": arguments,
                    "shutter_id": shutter_id,
                    "command": arguments[1],
                    "counter": counter,
                    "frame": frame_to_string(frame),
                    "shutter": arguments[0],
                }
            )
    return decoded_commands


def main():
    """Test the interpreter."""
    print(decode_json_commands("settings.json", "night_down"))
    # print(decode_str_commands("settings.json",
    #       "send('figuier', 'up')\nsend('figuier', 'up', 2543)\n"
    #                           "send('figuier', 'up', 2543)"))


if __name__ == "__main__":
    main()
