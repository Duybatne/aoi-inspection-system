"""
Unit tests for core/inference_engine/detector.py
"""
import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from core.inference_engine.detector import (
    MockDetector,
    RoboflowDetector,
    DetectorFactory,
    BaseDetector,
)


def _blank_image(w=640, h=640):
    return np.zeros((h, w, 3), dtype=np.uint8)


class TestMockDetector:
    def test_returns_list(self):
        detector = MockDetector(confidence_threshold=0.5)
        result = detector.detect(_blank_image())
        assert isinstance(result, list)

    def test_no_defect_file_returns_empty(self, tmp_path, monkeypatch):
        detector = MockDetector(confidence_threshold=0.5)
        # Ensure no .mock_defects.json exists in tmp_path
        result = detector.detect(_blank_image())
        assert result == []

    def test_is_base_detector(self):
        assert issubclass(MockDetector, BaseDetector)


class TestDetectorFactory:
    def test_no_api_key_returns_mock(self):
        settings = MagicMock()
        settings.ROBOFLOW_API_KEY = ""
        settings.CONFIDENCE_THRESHOLD = 0.5
        detector = DetectorFactory.create(settings)
        assert isinstance(detector, MockDetector)

    def test_with_api_key_returns_roboflow(self):
        settings = MagicMock()
        settings.ROBOFLOW_API_KEY = "test-key-123"
        settings.ROBOFLOW_MODEL_ID = "pcb/1"
        settings.ROBOFLOW_API_URL = "https://detect.roboflow.com"
        settings.CONFIDENCE_THRESHOLD = 0.5
        detector = DetectorFactory.create(settings)
        assert isinstance(detector, RoboflowDetector)


class TestRoboflowDetector:
    def test_returns_empty_on_api_failure(self):
        detector = RoboflowDetector(
            api_key="fake-key",
            model_id="model/1",
            api_url="https://detect.roboflow.com",
            confidence_threshold=0.5,
        )
        # Should not raise — returns [] on HTTP error
        with patch("core.inference_engine.detector.requests.post", side_effect=Exception("network error")):
            result = detector.detect(_blank_image())
        assert result == []

    def test_parses_roboflow_response(self):
        detector = RoboflowDetector(
            api_key="fake-key",
            model_id="model/1",
            api_url="https://detect.roboflow.com",
            confidence_threshold=0.5,
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "predictions": [
                {
                    "x": 100, "y": 100, "width": 50, "height": 50,
                    "confidence": 0.92, "class": "missing", "class_id": 0
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        with patch("requests.post", return_value=mock_response):
            result = detector.detect(_blank_image())
        assert len(result) == 1
        assert result[0]["class_name"] == "missing"
        assert result[0]["confidence"] == pytest.approx(0.92, abs=0.001)
        assert result[0]["x_min"] == pytest.approx(75.0)
        assert result[0]["x_max"] == pytest.approx(125.0)
