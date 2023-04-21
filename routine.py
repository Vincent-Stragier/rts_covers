#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# scp E:\Vincent\Bureau\email_server.py root@omv-vincent.local:/etc/sunset/
# git pull && ./install.sh && watch systemctl status sunset
# git pull & chmod +x install.sh & chmod 777 install.sh & ./install.sh
# watch systemctl status sunset
# Generate requirements.txt
# pipreqs --force
# TODO:
# [x] save settings and counters (email them)
# [] ...

import os
import time
import multiprocessing as mp

import somfy_frame_generator as frame_generator
from interpreter import decode_str_commands
from uart import UART


SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")


def http_server(logger, remote: UART, port: int = 42):
    """Setup HTTP server.

    To interact with the blinds:
    http://hostname:port/?name=<a_name>&action=<valid_action>

    To interact with the pins:
    http://hostname:port/?pin=<pin_number>&delay=<delay_in_ms>
    """
    from flask import Flask, request
    app = Flask(__name__)

    @app.route('/', methods=['GET', 'POST'])
    def args():
        # list received parameters
        if request.method == 'GET':
            command = None
            parameters = dict(request.args)

            if ('name' in parameters) and ('action' in parameters):
                # logger.info(f"{request.args} seems valid...")
                command = f'send(\'{parameters["name"]}\', \'{parameters["action"]}\')'

            elif ('pin' in parameters) and ('delay' in parameters):
                command = f'pulse({parameters["pin"]}, {parameters["delay"]})'

            # Send command to remote
            if command is not None:
                logger.debug(command)
                if command.startswith('send'):
                    decoded_command = decode_str_commands(
                        SETTINGS_FILE, command)[0]
                else:
                    decoded_command = {'frame': command}

                logger.debug(f'In HTTP server {decoded_command = }')

                remote.reset_input_buffer()
                # Send frame on UART
                # logger.debug(f'???? {decoded_command["frame"].encode() = }')
                remote.write(decoded_command['frame'].encode(), flush=True)
                # Wait up to 10 s to receive the reply from UART
                uart_response = remote.read_all(_timeout=10)
                # Validate that the right command has been sent
                check_command = decoded_command['frame'].encode(
                ) in uart_response

                # Increment remote counter
                if command.startswith('send'):
                    if check_command and len(decoded_command['arguments']) == 2:
                        frame_generator.increment_shutter_counter(
                            SETTINGS_FILE, decoded_command['shutter'])

                logger.debug(f"UART TX {decoded_command['frame'].encode()}")
                logger.debug(f"UART RX {uart_response}")
                logger.debug(f"TX == RX: {check_command}")
                if uart_response:
                    return f"\nTX: {uart_response.decode()}"
                else:
                    return "S: No response from remote."

            logger.debug(f'In HTTP server {request.args}')
            return str(request.args)

    logger.info(f"Start flask server on port {port}...")
    app.run(port=port, host="0.0.0.0")


def main():
    # Configure logging
    import json
    import daemon
    from cysystemd import journal
    import logging

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%d/%m/%Y %I:%M:%S %p",
    )
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Create formatter for the logs
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%d/%m/%Y %I:%M:%S %p",
        style="%",
    )

    fh = logging.FileHandler(os.path.join(
        os.path.dirname(__file__), "rts_covers.log"))
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(journal.JournaldLogHandler())

    context = daemon.DaemonContext(files_preserve=[fh.stream])

    # Create a mocked context manager
    class MockedContextManager:
        def __enter__(self):
            logger.debug("Entering mocked context...")

        def __exit__(self, exc_type, exc_value, exc_tb):
            logger.debug("Leaving mocked context...")
            logger.debug(f"{exc_type}\n{exc_value}\n{exc_tb}\n")

    # Suboptimal to load two times the parameters...
    config_file = SETTINGS_FILE
    settings = frame_generator.read_config_file(config_file)
    if settings["Test"]["context_mocking"]:
        context = MockedContextManager()

    with context:
        logger.info("Logging is starting.")
        logger.debug(f"Settings' file: {config_file}")
        logger.debug("Dump settings:")
        logger.debug(json.dumps(settings, indent=4))

        # Extract the settings of the shutters
        logger.info("Retrieve shutters settings.")
        counters_root = frame_generator.counters_path(config_file)
        # Read each counter value or create counter file
        counters_paths = []
        for _, conf in settings["shutters"].items():
            # int(conf["id"], 16)
            counter_path = os.path.join(counters_root, f"{conf['id']}.txt")
            counters_paths.append(counter_path)
            try:
                shutter_id = conf['id']
                counter_value = frame_generator.read_counter(counter_path)
                logger.info(
                    f"Counter value for {shutter_id}: {counter_value}")
            except FileNotFoundError:
                logger.info(f"Create counter file for {conf['id']}")
                frame_generator.save_counter(counter_path)
        # counters_and_settings_paths = counters_paths + [SETTINGS_FILE]
        # Initialize the remote
        logger.info("Initialize remote (UART link).")

        while True:
            try:
                http_process = None

                # Initialize the remote
                vid_sr = settings["UART"]["VID_SR"]
                bauderate = settings["UART"]["SPEED"]
                timeout = 0.1
                mocking = settings["Test"]["remote_mocking"]
                logger.debug(f"{vid_sr = }")
                logger.debug(f"{bauderate = }")
                logger.debug(f"{timeout = }")
                logger.debug(f"{mocking = }")
                remote = UART(vid_sr, bauderate, timeout, mocking)

                if settings["Test"]["remote_mocking"]:
                    logger.debug("The remote is being mocked.")
                else:
                    assert remote.connect(2)

                # Initialize HTTP server (multiprocessing)
                if settings["HTTP"]["enable"]:
                    logger.info("Start HTTP server.")
                    http_process = mp.Process(
                        target=http_server,
                        args=(logger, remote, settings["HTTP"]["port"])
                    ).start()
                else:
                    logger.debug("Not starting HTTP server.")

            except Exception:
                import traceback
                logger.error(traceback.format_exc())

            finally:
                if http_process is not None:
                    http_process.terminate()
                remote.disconnect()

            # Wait for the remote to be reconnected
            logger.info("Remote disconnected. Wait for reconnection...")
            time.sleep(3)


if __name__ == "__main__":
    main()
