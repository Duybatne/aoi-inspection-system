import logging
from typing import Dict, Any
from hardware.lighting_control.base_lighting import BaseLighting

logger = logging.getLogger("MockLighting")


class MockLighting(BaseLighting):
    """
    Simulated ring light for development and testing.
    Logs all commands without any serial communication.
    """

    def __init__(self):
        self._on = False
        self._intensity = 80  # default intensity %

    def power_on(self) -> None:
        self._on = True
        logger.info(f"[MockLighting] Power ON (intensity={self._intensity}%)")

    def power_off(self) -> None:
        self._on = False
        logger.info("[MockLighting] Power OFF")

    def set_intensity(self, intensity: int) -> None:
        if not 0 <= intensity <= 100:
            raise ValueError(f"Intensity must be 0-100, got {intensity}")
        self._intensity = intensity
        logger.info(f"[MockLighting] Intensity set to {intensity}%")

    def get_status(self) -> Dict[str, Any]:
        return {"powered": self._on, "intensity": self._intensity, "type": "mock"}
