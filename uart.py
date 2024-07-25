"""UART class to handle the serial port communication."""

from __future__ import annotations

import multiprocessing as mp
import time

import serial
import serial.tools.list_ports as serial_list_ports


class UART:
    """UART class to handle the serial port communication."""

    def __init__(
        self,
        vid_pid: str,
        baudrate: int = 115200,
        timeout: float = 0.1,
        mocking: bool = False,
    ) -> None:
        self.ser = serial.Serial()
        self.vid_pid = vid_pid
        self.ser.baudrate = baudrate
        self.ser.timeout = timeout
        self.lock = mp.Lock()
        self.mock = mocking

    def get_port(self) -> bool:
        """Scan ports.

        Returns:
            False, if no port corresponding to the VID is found.
            Else, return the port for the corresponding.
        """
        if self.mock:
            return None

        ls_ports = [tuple(p) for p in list(serial_list_ports.comports())]

        for port in ls_ports:
            if self.vid_pid in port[2]:
                return port[0]
        return False

    def connect(self, timeout: float = 0) -> bool:
        """Initiate the connection to the serial port.

        Args:
            timeout: time to wait before releasing the lock.
        """
        if self.mock:
            return True

        try:
            self.lock.acquire()
            self.ser.port = self.get_port()
            self.ser.open()
            init_t = time.time()

            # Wait for message or timeout
            while not (time.time() - init_t >= timeout or self.ser.in_waiting):
                continue

            time.sleep(0.01)
            self.lock.release()

            return self.ser.is_open

        except ConnectionError:
            self.lock.release()
            return False

    def disconnect(self) -> bool:
        """Disconnect the serial port.

        Returns:
            True, if the disconnection is successful, else, False.
        """
        if self.mock:
            return True

        self.lock.acquire()
        self.ser.close()
        self.lock.release()

        return not self.ser.is_open

    def reconnect(self, timeout: float = 0) -> bool:
        """Disconnect and reconnect the serial port.

        Returns:
            True, if the disconnection and reconnection are successful,
            else, False.
        """
        if self.mock:
            return True

        return self.disconnect() and self.connect(timeout)

    def write(self, _bytes, flush: bool = False) -> bool:
        """Write bytes on the serial port.

        Args:
            _bytes: the bytes array to write on the serial port.
            flush: flush the serial port.

        Returns:
            True if success, else, False.
        """
        if self.mock:
            return True

        try:
            if self.ser.is_open:
                self.lock.acquire()
                self.ser.write(_bytes)

                if flush:
                    self.ser.flush()

                self.lock.release()
                return True

            return False

        except ConnectionError:
            self.lock.release()
            return False

    def send(self, message: str | bytes | any, flush: bool = True) -> None:
        """Write a message on the serial port.

        Args:
            message: the string to write on the serial port.
            flush: flush the serial port.

        Returns:
            True if success, else, False.
        """
        if self.mock:
            return

        if isinstance(message, str):
            self.write(message.encode("utf-8"), flush)

        elif isinstance(message, bytes):
            self.write(message, flush)

        raise ValueError("Invalid message type")

    def read_all(self, _timeout: float = 0) -> bool | None:
        """Read all the bytes on the serial port."""
        if self.mock:
            return b"Mocking"

        self.lock.acquire()
        start_time = time.perf_counter()

        try:
            if not self.ser.is_open:
                self.lock.release()
                return None

            while (
                not self.ser.in_waiting
                and time.perf_counter() - start_time < _timeout
            ):
                time.sleep(0.01)

            bytes_buffer = b""
            while self.ser.in_waiting > 0:
                bytes_buffer += self.ser.read(self.ser.in_waiting)
                time.sleep(self.ser.timeout)
            self.lock.release()

            return bytes_buffer

        except ConnectionError:
            self.lock.release()
            return False

    def in_waiting(self) -> int:
        """Return the number of bytes in the input buffer."""
        if self.mock:
            return 0

        self.lock.acquire()
        in_waiting = self.ser.in_waiting
        self.lock.release()

        return in_waiting

    def reset_input_buffer(self) -> None:
        """Reset the input buffer."""
        if self.mock:
            return

        self.lock.acquire()
        if self.ser.is_open:
            self.ser.reset_input_buffer()

        self.lock.release()

    def check(self, timeout: int = 5) -> bool:
        """Check if the serial port is open."""
        if self.mock:
            return True

        self.lock.acquire()

        if self.get_port():
            self.lock.release()
            return True

        try:  # self.get_port() is False, retry
            if self.get_port():
                self.ser.close()
                self.ser.port = self.get_port()
                self.ser.open()

                # Wait for message or timeout
                start_time = time.time()
                while time.time() - start_time < timeout:

                    if self.ser.in_waiting:
                        time.sleep(0.01)
                        break

            self.lock.release()
            return self.ser.is_open

        except ConnectionError:
            self.lock.release()
            return False

    def is_mocking(self) -> bool:
        """Return True if the serial port is mocking."""
        return self.mock
