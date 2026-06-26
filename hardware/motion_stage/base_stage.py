from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any


class BaseStage(ABC):
    """Abstract interface for XY motion stage controllers."""

    @abstractmethod
    def home(self) -> None:
        """Move stage to home position and reset coordinates."""

    @abstractmethod
    def move_to(self, x: float, y: float) -> None:
        """
        Move stage to absolute coordinates (in mm).

        Args:
            x: Target X position in mm.
            y: Target Y position in mm.
        """

    @abstractmethod
    def get_position(self) -> Tuple[float, float]:
        """Return current (x, y) position in mm."""

    @abstractmethod
    def is_ready(self) -> bool:
        """Return True if stage is homed and not moving."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Return current stage status dict."""
