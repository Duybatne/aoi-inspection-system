import logging
import cv2
import numpy as np

logger = logging.getLogger("PreprocessingPipeline")


class PreprocessingPipeline:
    """
    Prepares a raw PCB image for inference.

    Steps (all configurable, all safe to skip):
        1. Resize to target dimensions (keeps aspect ratio with padding)
        2. Optional CLAHE contrast enhancement
        3. Normalize pixel values to [0, 1] (for model input if needed)
        4. Return processed BGR image (or normalized float array)
    """

    def __init__(
        self,
        target_size: tuple = (640, 640),
        apply_clahe: bool = True,
        normalize: bool = False,
    ):
        self.target_size = target_size  # (width, height)
        self.apply_clahe = apply_clahe
        self.normalize = normalize
        self._clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    def run(self, image: np.ndarray) -> np.ndarray:
        """
        Applies the full preprocessing pipeline.

        Args:
            image: BGR image (np.ndarray, uint8)

        Returns:
            Processed image. dtype=uint8 unless normalize=True (float32 [0,1]).
        """
        if image is None or image.size == 0:
            raise ValueError("PreprocessingPipeline received an empty image.")

        img = self._letterbox(image, self.target_size)

        if self.apply_clahe:
            img = self._apply_clahe(img)

        if self.normalize:
            img = img.astype(np.float32) / 255.0

        logger.debug(f"Preprocessing done: output shape={img.shape}, dtype={img.dtype}")
        return img

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _letterbox(self, image: np.ndarray, target_size: tuple) -> np.ndarray:
        """
        Resize + pad to target_size while keeping aspect ratio.
        Padding color: (114, 114, 114) — standard YOLO letterbox.
        """
        tw, th = target_size
        ih, iw = image.shape[:2]
        scale = min(tw / iw, th / ih)
        new_w = int(iw * scale)
        new_h = int(ih * scale)

        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        canvas = np.full((th, tw, 3), 114, dtype=np.uint8)
        pad_x = (tw - new_w) // 2
        pad_y = (th - new_h) // 2
        canvas[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized
        return canvas

    def _apply_clahe(self, image: np.ndarray) -> np.ndarray:
        """Apply CLAHE to the L channel in LAB color space."""
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l_enhanced = self._clahe.apply(l)
        lab_enhanced = cv2.merge([l_enhanced, a, b])
        return cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
