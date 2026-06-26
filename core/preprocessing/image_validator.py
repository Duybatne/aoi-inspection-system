import logging
import cv2
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger("ImageValidator")


@dataclass
class ValidationResult:
    ok: bool
    reason: str = ""


class ImageValidator:
    """
    Validates a PCB image before it enters the inference pipeline.

    Checks performed:
        1. Not None / empty
        2. Minimum resolution
        3. Brightness (mean pixel value) within acceptable range
        4. Blur (Laplacian variance) above a sharpness threshold
    """

    def __init__(
        self,
        min_width: int = 320,
        min_height: int = 240,
        blur_threshold: float = 100.0,
        brightness_min: float = 30.0,
        brightness_max: float = 230.0,
    ):
        self.min_width = min_width
        self.min_height = min_height
        self.blur_threshold = blur_threshold
        self.brightness_min = brightness_min
        self.brightness_max = brightness_max

    def validate(self, image: np.ndarray) -> ValidationResult:
        # 1. Non-empty check
        if image is None or image.size == 0:
            return ValidationResult(ok=False, reason="Image is empty or None.")

        h, w = image.shape[:2]

        # 2. Resolution check
        if w < self.min_width or h < self.min_height:
            return ValidationResult(
                ok=False,
                reason=f"Image too small: {w}x{h}, minimum {self.min_width}x{self.min_height}."
            )

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 3. Brightness check
        mean_brightness = float(np.mean(gray))
        if mean_brightness < self.brightness_min:
            return ValidationResult(
                ok=False,
                reason=f"Image too dark (mean brightness={mean_brightness:.1f} < {self.brightness_min})."
            )
        if mean_brightness > self.brightness_max:
            return ValidationResult(
                ok=False,
                reason=f"Image overexposed (mean brightness={mean_brightness:.1f} > {self.brightness_max})."
            )

        # 4. Blur (sharpness) check via Laplacian variance
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        if laplacian_var < self.blur_threshold:
            return ValidationResult(
                ok=False,
                reason=f"Image too blurry (Laplacian variance={laplacian_var:.1f} < {self.blur_threshold})."
            )

        logger.info(
            f"Image validated: {w}x{h}, brightness={mean_brightness:.1f}, sharpness={laplacian_var:.1f}"
        )
        return ValidationResult(ok=True)
