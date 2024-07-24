"""Somfy RTS integration for Home Assistant."""

import requests


class RTSSomfyRollingShutter:
    """Representation of a Somfy RTS rolling shutter."""

    def __init__(self, ip_address, port, shutter_name) -> None:
        self.ip_address = ip_address
        self.port = port
        self.name = shutter_name

    def _send_action(self, action):
        return requests.get(
            f"http://{self.ip_address}:{self.port}/"
            f"?name={self.name}&action={action}"
        ).content

    def stop(self):
        """Stop the rolling shutter."""
        return self._send_action(action="stop")

    def down(self):
        """Move the rolling shutter down."""
        return self._send_action(action="down")

    def up(self):
        """Move the rolling shutter up."""
        return self._send_action(action="up")
