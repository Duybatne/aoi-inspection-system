from abc import ABC, abstractmethod
from typing import Dict, Any
import numpy as np


class BaseCamera(ABC):
    """
    Abstract interface for all camera drivers (mock, Basler, Allied Vision, etc.).

    All concrete implementations must satisfy this contract so that the
    rest of the pipeline is camera-agnostic.
    """

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the camera. Returns True on success."""

    @abstractmethod
    def disconnect(self) -> bool:
        """Release the camera connection. Returns True on success."""

    @abstractmethod
    def start_grabbing(self) -> bool:
        """Start the image acquisition loop. Returns True on success."""

    @abstractmethod
    def stop_grabbing(self) -> bool:
        """Stop the image acquisition loop. Returns True on success."""

    @abstractmethod
    def capture_frame(self, **kwargs) -> np.ndarray:
        """
        Capture a single frame.

        Returns:
            np.ndarray: BGR image.
        """

    @abstractmethod
    def set_exposure(self, exposure_time: float) -> None:
        """Set exposure time in microseconds."""

    @abstractmethod
    def set_gain(self, gain: float) -> None:
        """Set gain in dB."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Return current camera status as a dict."""
