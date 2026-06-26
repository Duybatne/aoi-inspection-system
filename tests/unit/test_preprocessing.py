"""
Unit tests for core/preprocessing/image_validator.py
"""
import numpy as np
import cv2
import pytest
from core.preprocessing.image_validator import ImageValidator, ValidationResult


@pytest.fixture
def validator():
    return ImageValidator(
        min_width=100,
        min_height=100,
        blur_threshold=50.0,
        brightness_min=30.0,
        brightness_max=230.0,
    )


def _make_image(width=640, height=480, brightness=128, blur=False):
    """Helper: create a synthetic BGR test image."""
    img = np.full((height, width, 3), brightness, dtype=np.uint8)
    # Add some texture so Laplacian detects edges
    img[::10, :] = np.clip(brightness + 40, 0, 255)
    if blur:
        img = cv2.GaussianBlur(img, (31, 31), 0)
    return img


class TestImageValidator:
    def test_valid_image_passes(self, validator):
        img = _make_image()
        result = validator.validate(img)
        assert result.ok, f"Expected valid image to pass: {result.reason}"

    def test_none_image_fails(self, validator):
        result = validator.validate(None)
        assert not result.ok
        assert "empty" in result.reason.lower() or "none" in result.reason.lower()

    def test_too_small_fails(self, validator):
        img = _make_image(width=50, height=50)
        result = validator.validate(img)
        assert not result.ok
        assert "small" in result.reason.lower()

    def test_too_dark_fails(self, validator):
        img = _make_image(brightness=10)
        result = validator.validate(img)
        assert not result.ok
        assert "dark" in result.reason.lower()

    def test_overexposed_fails(self, validator):
        img = _make_image(brightness=250)
        result = validator.validate(img)
        assert not result.ok
        assert "overexposed" in result.reason.lower()

    def test_blurry_image_fails(self, validator):
        img = _make_image(blur=True)
        result = validator.validate(img)
        # Blurry images should fail sharpness check
        assert not result.ok
        assert "blur" in result.reason.lower()

    def test_result_is_dataclass(self, validator):
        img = _make_image()
        result = validator.validate(img)
        assert isinstance(result, ValidationResult)
        assert hasattr(result, "ok")
        assert hasattr(result, "reason")
