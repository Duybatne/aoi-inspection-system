import logging
import requests
import base64
import cv2
import numpy as np
from abc import ABC, abstractmethod
from typing import List, Dict, Any

logger = logging.getLogger("InferenceEngine")


# ---------------------------------------------------------------------------
# Abstract Base
# ---------------------------------------------------------------------------

class BaseDetector(ABC):
    """Common interface for all detector backends."""

    @abstractmethod
    def detect(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Run object detection on a BGR PCB image.

        Returns:
            List of dicts with keys:
                class_id, class_name, confidence, x_min, y_min, x_max, y_max
        """


# ---------------------------------------------------------------------------
# Roboflow Cloud Detector
# ---------------------------------------------------------------------------

class RoboflowDetector(BaseDetector):
    """
    Sends the image to Roboflow Hosted Inference API and returns detections.

    Docs: https://docs.roboflow.com/deploy/hosted-api/object-detection
    """

    def __init__(self, api_key: str, model_id: str, api_url: str, confidence_threshold: float = 0.5):
        self.api_key = api_key
        self.model_id = model_id
        self.api_url = api_url.rstrip("/")
        self.confidence_threshold = confidence_threshold
        logger.info(f"RoboflowDetector initialized: model={model_id}, url={api_url}")

    def detect(self, image: np.ndarray) -> List[Dict[str, Any]]:
        # Encode image as JPEG → base64
        _, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 90])
        img_b64 = base64.b64encode(buffer.tobytes()).decode("utf-8")

        url = f"{self.api_url}/{self.model_id}"
        params = {"api_key": self.api_key, "confidence": int(self.confidence_threshold * 100)}

        try:
            response = requests.post(
                url,
                params=params,
                data=img_b64,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.error(f"Roboflow API request failed: {e}")
            return []

        img_h, img_w = image.shape[:2]
        defects = []
        for pred in data.get("predictions", []):
            # Roboflow returns center x/y + width/height (normalized or absolute)
            cx = pred.get("x", 0)
            cy = pred.get("y", 0)
            w = pred.get("width", 0)
            h = pred.get("height", 0)
            conf = pred.get("confidence", 0.0)
            class_name = pred.get("class", "unknown")

            if conf < self.confidence_threshold:
                continue

            defects.append({
                "class_id": pred.get("class_id", 0),
                "class_name": class_name,
                "confidence": round(conf, 4),
                "x_min": float(cx - w / 2),
                "y_min": float(cy - h / 2),
                "x_max": float(cx + w / 2),
                "y_max": float(cy + h / 2),
            })

        logger.info(f"Roboflow detected {len(defects)} defects.")
        return defects


# ---------------------------------------------------------------------------
# Mock Detector (dev / fallback)
# ---------------------------------------------------------------------------

class MockDetector(BaseDetector):
    """
    Mock detector for development and CI — reads .mock_defects.json written
    by MockCamera, simulating what a real model would return.
    """

    def __init__(self, confidence_threshold: float = 0.5):
        import os, json
        self.confidence_threshold = confidence_threshold
        self._os = os
        self._json = json
        logger.warning("MockDetector active — using simulated defect data.")

    def detect(self, image: np.ndarray) -> List[Dict[str, Any]]:
        import os, json
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        filepath = os.path.join(root_dir, ".mock_defects.json")

        if not os.path.exists(filepath):
            logger.info("MockDetector: no defect file found — PASS.")
            return []

        try:
            with open(filepath, "r") as f:
                defects = json.load(f)
            os.remove(filepath)
            filtered = [d for d in defects if d.get("confidence", 1.0) >= self.confidence_threshold]
            logger.info(f"MockDetector: {len(filtered)} simulated defects.")
            return filtered
        except Exception as e:
            logger.error(f"MockDetector: error reading defect file: {e}")
            return []


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class DetectorFactory:
    """
    Selects the appropriate detector backend based on configuration.

    Priority:
        1. RoboflowDetector  — if ROBOFLOW_API_KEY is set
        2. MockDetector      — fallback (dev / no credentials)
    """

    @staticmethod
    def create(settings) -> BaseDetector:
        if settings.ROBOFLOW_API_KEY:
            logger.info("DetectorFactory: selecting RoboflowDetector (cloud).")
            return RoboflowDetector(
                api_key=settings.ROBOFLOW_API_KEY,
                model_id=settings.ROBOFLOW_MODEL_ID,
                api_url=settings.ROBOFLOW_API_URL,
                confidence_threshold=settings.CONFIDENCE_THRESHOLD,
            )

        logger.warning("DetectorFactory: ROBOFLOW_API_KEY not set, falling back to MockDetector.")
        return MockDetector(confidence_threshold=settings.CONFIDENCE_THRESHOLD)


# Backward-compatible alias (used in existing tasks.py)
YOLOv11Detector = MockDetector
