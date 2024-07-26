"""Create a web server to interact with the covers and the pins."""

import time
from multiprocessing import Lock

from flask import Flask, request, current_app

import somfy_frame_generator as frame_generator
from interpreter import decode_str_commands

from uart import UART

web_app = Flask(__name__)

request_lock = Lock()


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


def _check_remote(remote: UART, logger) -> bool:
    """Check if the remote is connected.

    Args:
        remote (UART): The remote object.
    """
    if not remote.check():
        logger.info("The remote is not connected.")
        logger.info("Will try to connect.")

        if remote.connect():
            logger.info("The remote is now connected.")

        else:
            logger.error("Could not connect to the remote.")
            logger.error("Will try again on request.")


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


def _decode_command(command: str, config_file_path) -> dict:
    """Decode the command.

    Args:
        command (str): The command.

    Returns:
        dict: The decoded command.
    """
    if command.startswith("send"):
        return decode_str_commands(config_file_path, command)[0]

    return {"frame": command}


# Setup HTTP server.

# To interact with the blinds:
# http://hostname:port/?name=<a_name>&action=<valid_action>

# To interact with the pins:
# http://hostname:port/?pin=<pin_number>&delay=<delay_in_ms>


@web_app.route("/", methods=["GET", "POST"])
def args():
    """Handle the requests."""
    with request_lock:
        logger = current_app.config["LOGGER"]
        remote = current_app.config["REMOTE"]

        # If the remote is not connected, try to connect
        _check_remote(remote, logger)

        if request.method not in ("GET", "POST"):
            return (
                "S: Invalid request method ("
                f"{request.method}), use GET or POST."
            )

        parameters = dict(request.args)
        command = _extract_command(parameters)

        # Send command to remote
        if command is not None:

            logger.debug(command)
            decoded_command = _decode_command(
                command, current_app.config["SETTINGS_FILE"]
            )

            logger.debug(
                "In HTTP server decoded_command = %s", decoded_command
            )

            # Check and retry if needed
            for try_index in range(10):
                uart_response, check_command = _send_to_remote(
                    remote, decoded_command
                )

                if check_command:
                    break

                logger.error(
                    (
                        "Command failed (%s), reconnecting remote"
                        " and retrying... (%s)"
                    ),
                    command,
                    try_index,
                )

                if remote.disconnect():
                    logger.debug("The remote is now disconnected.")

                else:
                    logger.error("Could not disconnect the remote.")

                time.sleep((try_index + 1) * 2)

                if remote.connect():
                    logger.debug("The remote is now connected.")

                else:
                    logger.error("Could not connect the remote.")

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
