import logging
import time
import serial
from typing import Dict, Any
from hardware.lighting_control.base_lighting import BaseLighting

logger = logging.getLogger("SerialLighting")


class SerialLightingError(Exception):
    pass


class SerialLighting(BaseLighting):
    """
    Controls an RS-232/RS-485 ring light controller via serial port.

    Protocol (ASCII):
        Power ON / set intensity:  "L{intensity:03d}\\r\\n"  e.g. "L080\\r\\n"
        Power OFF:                 "L000\\r\\n"

    Adjust command format to match your specific lighting controller.
    """

    def __init__(self, port: str = "/dev/ttyUSB0", baudrate: int = 9600, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._intensity = 80
        self._on = False
        self._serial: serial.Serial | None = None

    def _open(self) -> serial.Serial:
        if self._serial is None or not self._serial.is_open:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
            )
            logger.info(f"SerialLighting: opened port {self.port} @ {self.baudrate} baud.")
        return self._serial

    def _send(self, command: str) -> None:
        try:
            conn = self._open()
            conn.write(command.encode("ascii"))
            time.sleep(0.05)  # allow controller to process
            logger.debug(f"SerialLighting: sent '{command.strip()}'")
        except serial.SerialException as e:
            raise SerialLightingError(f"Serial write failed: {e}") from e

    def power_on(self) -> None:
        self._send(f"L{self._intensity:03d}\r\n")
        self._on = True
        logger.info(f"SerialLighting: power ON (intensity={self._intensity}%)")

    def power_off(self) -> None:
        self._send("L000\r\n")
        self._on = False
        logger.info("SerialLighting: power OFF")

    def set_intensity(self, intensity: int) -> None:
        if not 0 <= intensity <= 100:
            raise ValueError(f"Intensity must be 0-100, got {intensity}")
        self._intensity = intensity
        if self._on:
            self._send(f"L{intensity:03d}\r\n")
        logger.info(f"SerialLighting: intensity set to {intensity}%")

    def get_status(self) -> Dict[str, Any]:
        return {
            "powered": self._on,
            "intensity": self._intensity,
            "port": self.port,
            "type": "serial",
        }

    def close(self) -> None:
        if self._serial and self._serial.is_open:
            self._serial.close()
            logger.info("SerialLighting: port closed.")
