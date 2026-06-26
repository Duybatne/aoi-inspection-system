from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseLighting(ABC):
    """Abstract interface for lighting controller drivers."""

    @abstractmethod
    def power_on(self) -> None:
        """Turn lighting on at current intensity."""

    @abstractmethod
    def power_off(self) -> None:
        """Turn lighting off."""

    @abstractmethod
    def set_intensity(self, intensity: int) -> None:
        """
        Set brightness level.

        Args:
            intensity: 0 (off) to 100 (maximum).
        """

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Return current lighting status."""
