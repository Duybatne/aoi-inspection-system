import logging
from hardware.camera_drivers.base_camera import BaseCamera
from hardware.camera_drivers.mock_camera import MockCamera

logger = logging.getLogger("CameraFactory")


class CameraNotAvailableError(Exception):
    """Raised when the requested camera driver is unavailable."""


class CameraFactory:
    """
    Instantiates the correct camera driver based on the configured type.

    Supported types:
        "mock"   — MockCamera (synthetic PCB images, always available)

    Future types (add driver + import here when hardware is available):
        "basler" — BaslerCamera (requires pypylon SDK)
        "allied" — AlliedVisionCamera (requires VimbaPython SDK)
    """

    @staticmethod
    def create(camera_type: str = "mock", camera_id: int = 0) -> BaseCamera:
        cam_type = camera_type.lower().strip()

        if cam_type == "mock":
            logger.info("CameraFactory: using MockCamera.")
            return MockCamera(camera_id=camera_id)

        if cam_type == "basler":
            try:
                from hardware.camera_drivers.basler_camera import BaslerCamera  # noqa: future
                logger.info("CameraFactory: using BaslerCamera.")
                return BaslerCamera(camera_id=camera_id)
            except ImportError:
                raise CameraNotAvailableError(
                    "BaslerCamera requires 'pypylon' SDK. "
                    "Install it or set CAMERA_TYPE=mock."
                )

        raise CameraNotAvailableError(
            f"Unknown camera type: '{camera_type}'. Supported: mock, basler."
        )
