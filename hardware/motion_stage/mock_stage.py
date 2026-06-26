import logging
import time
from typing import Tuple, Dict, Any
from hardware.motion_stage.base_stage import BaseStage

logger = logging.getLogger("MockStage")

# Simulated movement speed (mm/s)
_STAGE_SPEED_MM_S = 50.0


class MockStage(BaseStage):
    """
    Simulated XY motion stage for development and testing.
    Simulates movement delay based on distance and speed.
    """

    def __init__(self):
        self._x: float = 0.0
        self._y: float = 0.0
        self._homed: bool = False
        self._moving: bool = False

    def home(self) -> None:
        logger.info("[MockStage] Homing...")
        self._moving = True
        time.sleep(0.5)  # simulate homing time
        self._x = 0.0
        self._y = 0.0
        self._homed = True
        self._moving = False
        logger.info("[MockStage] Homed at (0, 0)")

    def move_to(self, x: float, y: float) -> None:
        if not self._homed:
            raise RuntimeError("Stage is not homed. Call home() first.")
        distance = ((x - self._x) ** 2 + (y - self._y) ** 2) ** 0.5
        delay = distance / _STAGE_SPEED_MM_S
        logger.info(f"[MockStage] Moving ({self._x:.1f}, {self._y:.1f}) → ({x:.1f}, {y:.1f}), ETA={delay:.2f}s")
        self._moving = True
        time.sleep(min(delay, 2.0))  # cap simulated delay at 2 s
        self._x = x
        self._y = y
        self._moving = False
        logger.info(f"[MockStage] Arrived at ({x:.1f}, {y:.1f})")

    def get_position(self) -> Tuple[float, float]:
        return self._x, self._y

    def is_ready(self) -> bool:
        return self._homed and not self._moving

    def get_status(self) -> Dict[str, Any]:
        return {
            "x": self._x,
            "y": self._y,
            "homed": self._homed,
            "moving": self._moving,
            "type": "mock",
        }
