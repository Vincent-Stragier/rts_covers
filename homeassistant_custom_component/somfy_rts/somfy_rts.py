import requests


class RTSSomfyRollingShutter():
    def __init__(self, ip_address, port, shutter_name) -> None:
        self.ip_address = ip_address
        self.port = port
        self.name = shutter_name

    def _send_action(self, action):
        return requests.get(f'http://{self.ip_address}:{self.port}/?name={self.name}&action={action}').content

    def stop(self):
        return self._send_action(action='stop')

    def down(self):
        return self._send_action(action='down')

    def up(self):
        return self._send_action(action='up')
