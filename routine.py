#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Main routine of the project."""

# scp E:\Vincent\Bureau\email_server.py root@omv-vincent.local:/etc/sunset/
# git pull && ./install.sh && watch systemctl status sunset
# git pull & chmod +x install.sh & chmod 777 install.sh & ./install.sh
# watch systemctl status sunset
# Generate requirements.txt
# pipreqs --force
# TODOS:
# [x] save settings and counters (email them)
# [] ...

import json
import logging
import os

import daemon
from systemd import journal

import somfy_frame_generator as frame_generator
from uart import UART

from flask_route import web_app

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")


class MockedContextManager:
    """Mocked context manager."""

    def __init__(self, current_logger):
        self.logger = current_logger

    def __enter__(self):
        self.logger.debug("Entering mocked context...")

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.logger.debug("Leaving mocked context...")
        self.logger.debug("%s\n%s\n%s\n", exc_type, exc_value, exc_tb)


def display_settings(current_logger, config_file_path):
    """Display the settings and the counters."""
    _settings = frame_generator.read_config_file(config_file_path)

    current_logger.info("Logging is starting.")
    current_logger.debug("Settings' file: %s", config_file_path)
    current_logger.debug("Dump settings:")
    current_logger.debug(json.dumps(_settings, indent=4))

    # Extract the settings of the shutters
    current_logger.info("Retrieve shutters settings.")
    counters_root = frame_generator.counters_path(config_file_path)

    # Read each counter value or create counter file
    counters_paths = []
    for _, conf in _settings["shutters"].items():
        # int(conf["id"], 16)
        counter_path = os.path.join(counters_root, f"{conf['id']}.txt")
        counters_paths.append(counter_path)

        try:
            shutter_id = conf["id"]
            counter_value = frame_generator.read_counter(counter_path)
            current_logger.info(
                "Counter value for %s: %s", shutter_id, counter_value
            )

        except FileNotFoundError:
            current_logger.info("Create counter file for %s", conf["id"])

            frame_generator.save_counter(counter_path)


def init_logger(
    format_str: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    date_format: str = "%d/%m/%Y %I:%M:%S %p",
    logger_name: str = __name__,
    log_file_path: str = "rts_covers.log",
):
    """Initialize the logger.

    Args:
        format_str (str, optional): The format string.
        Defaults to "%(asctime)s - %(name)s - %(levelname)s - %(message)s".
        date_format (str, optional): The date format.
        Defaults to "%d/%m/%Y %I:%M:%S %p".
        logger_name (str, optional): The logger name. Defaults to __name__.
        log_file_path (str, optional): The log file path.
        Defaults to "rts_covers.log".

    Returns:
        tuple: The logger and the file handler.
    """
    logging.basicConfig(
        format=format_str,
        datefmt=date_format,
    )
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    # Create formatter for the logs
    formatter = logging.Formatter(
        fmt=format_str,
        datefmt=date_format,
        style="%",
    )

    file_handler = logging.FileHandler(
        os.path.join(os.path.dirname(__file__), log_file_path)
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(journal.JournalHandler(SYSLOG_IDENTIFIER=logger_name))

    return logger, file_handler


def main():
    """Main function."""
    logger, file_handler = init_logger()
    context = daemon.DaemonContext(files_preserve=[file_handler.stream])

    # Suboptimal to load two times the parameters...
    config_file = SETTINGS_FILE
    settings = frame_generator.read_config_file(config_file)

    if settings["Test"]["context_mocking"]:
        # Create a mocked context manager
        context = MockedContextManager(logger)

    with context:
        display_settings(logger, SETTINGS_FILE)

        # Initialize the remote
        logger.info("Initialize remote (UART link).")

        port = settings["HTTP"]["port"]
        vid_sr = settings["UART"]["VID_SR"]
        bauderate = settings["UART"]["SPEED"]
        timeout = 0.1
        mocking = settings["Test"]["remote_mocking"]

        logger.debug("vid_sr = %s", vid_sr)
        logger.debug("bauderate = %s", bauderate)
        logger.debug("timeout = %s", timeout)
        logger.debug("mocking = %s", mocking)

        remote = UART(vid_sr, bauderate, timeout, mocking)

        if settings["Test"]["remote_mocking"]:
            logger.debug("The remote is being mocked.")

        else:
            if not remote.connect(2):
                logger.error("Could not connect to the remote.")
                logger.error("Will try again on request.")

        # Save the logger and the remote in the app context
        web_app.config["LOGGER"] = logger
        web_app.config["REMOTE"] = remote
        web_app.config["SETTINGS_FILE"] = SETTINGS_FILE

        logger.info("Start flask server on port %s...", port)
        web_app.run(port=port, host="0.0.0.0")


if __name__ == "__main__":
    main()
