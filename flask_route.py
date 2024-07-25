"""The module that helps to create a web server to interact with the blinds and the pins."""

from flask import request, current_app

import somfy_frame_generator as frame_generator
from interpreter import decode_str_commands

from uart import UART


def _send_to_remote(
    current_remote: UART, current_decoded_command: dict, timeout: float = 10
):
    """Send a command to the remote.

    Args:
        remote (UART): The remote object.
        decoded_command (dict): The decoded command.
        timeout (int, optional): The timeout. Defaults to 10 seconds.

    Returns:
        tuple: The response and the response check.
    """
    current_remote.reset_input_buffer()

    current_remote.write(
        current_decoded_command["frame"].encode("utf-8"), flush=True
    )
    # Wait up to 10 s to receive the reply from UART
    uart_response = current_remote.read_all(_timeout=timeout)

    # Validate that the right command has been sent
    check_response = (
        current_decoded_command["frame"].encode("utf-8") in uart_response
    )

    return uart_response, check_response


def _extract_command(parameters: dict) -> str:
    """Extract the command from the parameters.

    Args:
        parameters (dict): The parameters.

    Returns:
        str: The command.
    """
    if ("name" in parameters) and ("action" in parameters):
        return (
            f'send(\'{parameters["name"]}\',' f' \'{parameters["action"]}\')'
        )

    if ("pin" in parameters) and ("delay" in parameters):
        return f'pulse({parameters["pin"]}, {parameters["delay"]})'

    return None


# Setup HTTP server.

# To interact with the blinds:
# http://hostname:port/?name=<a_name>&action=<valid_action>

# To interact with the pins:
# http://hostname:port/?pin=<pin_number>&delay=<delay_in_ms>


@current_app.route("/", methods=["GET", "POST"])
def args():
    """Handle the requests."""
    logger = current_app.config["LOGGER"]
    remote = current_app.config["REMOTE"]

    # If the remote is not connected, try to connect
    if not remote.check():
        logger.info("The remote is not connected.")
        logger.info("Will try to connect.")

        if remote.connect():
            logger.info("The remote is now connected.")

        else:
            logger.error("Could not connect to the remote.")
            logger.error("Will try again on request.")

    if not request.method in ("GET", "POST"):
        return (
            "S: Invalid request method ("
            f"{request.method}), use GET or POST."
        )

    parameters = dict(request.args)
    command = _extract_command(parameters)

    # Send command to remote
    if command is not None:

        logger.debug(command)
        if command.startswith("send"):
            decoded_command = decode_str_commands(
                current_app.config["SETTINGS_FILE"], command
            )[0]

        else:
            decoded_command = {"frame": command}

        logger.debug("In HTTP server decoded_command = %s", decoded_command)

        # Check and retry if needed
        for try_index in range(10):
            uart_response, check_command = _send_to_remote(
                remote, decoded_command
            )

            if check_command:
                break

            logger.error(
                (
                    "Command failed, reconnecting remote"
                    " and retrying... (%s)"
                ),
                try_index,
            )
            remote.reconnect()

        # Increment remote counter
        if command.startswith("send"):
            if check_command and len(decoded_command["arguments"]) == 2:
                frame_generator.increment_shutter_counter(
                    current_app.config["SETTINGS_FILE"],
                    decoded_command["shutter"],
                )

        logger.debug(
            "UART TX %s\nUART RX %s\nTX == RX: %s",
            decoded_command["frame"].encode("utf-8"),
            uart_response,
            check_command,
        )

        if uart_response:
            return f"\nTX: {uart_response.decode()}"

        return "S: No response from remote."

    logger.debug("In HTTP server %s", request.args)
    return str(request.args)
