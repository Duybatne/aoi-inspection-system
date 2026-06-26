import logging
import json
import os
import cv2
import numpy as np
from typing import Optional

logger = logging.getLogger("CameraCalibration")

_DEFAULT_CALIBRATION_PATH = "data/calibration_data.json"


class CameraCalibration:
    """
    Applies lens distortion correction using a pre-computed camera matrix.

    Usage:
        calib = CameraCalibration.load()
        undistorted = calib.undistort(raw_image)

    If no calibration file exists the image is returned unchanged (safe passthrough).
    Calibration data (camera_matrix, dist_coeffs) can be generated with:
        cv2.calibrateCamera() using a checkerboard pattern.
    """

    def __init__(self, camera_matrix: Optional[np.ndarray], dist_coeffs: Optional[np.ndarray]):
        self.camera_matrix = camera_matrix
        self.dist_coeffs = dist_coeffs
        self._active = camera_matrix is not None and dist_coeffs is not None

    @classmethod
    def load(cls, path: str = _DEFAULT_CALIBRATION_PATH) -> "CameraCalibration":
        """Load calibration from JSON file. Returns passthrough instance if not found."""
        if not os.path.exists(path):
            logger.warning(f"Calibration file not found at '{path}' — using passthrough (no undistortion).")
            return cls(camera_matrix=None, dist_coeffs=None)

        try:
            with open(path, "r") as f:
                data = json.load(f)
            camera_matrix = np.array(data["camera_matrix"], dtype=np.float64)
            dist_coeffs = np.array(data["dist_coeffs"], dtype=np.float64)
            logger.info(f"Calibration loaded from '{path}'.")
            return cls(camera_matrix=camera_matrix, dist_coeffs=dist_coeffs)
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse calibration file: {e} — using passthrough.")
            return cls(camera_matrix=None, dist_coeffs=None)

    def save(self, path: str = _DEFAULT_CALIBRATION_PATH) -> None:
        """Persist calibration data to JSON."""
        if not self._active:
            logger.warning("No calibration data to save.")
            return
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        data = {
            "camera_matrix": self.camera_matrix.tolist(),
            "dist_coeffs": self.dist_coeffs.tolist(),
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Calibration saved to '{path}'.")

    def undistort(self, image: np.ndarray) -> np.ndarray:
        """
        Apply lens undistortion. Returns original image if calibration is inactive.
        """
        if not self._active:
            return image
        return cv2.undistort(image, self.camera_matrix, self.dist_coeffs)

    @property
    def is_active(self) -> bool:
        return self._active
