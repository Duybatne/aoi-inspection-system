"""
Unit tests for core/verdict_engine/engine.py
"""
import pytest
from core.verdict_engine.engine import VerdictEngine, VerdictResult


@pytest.fixture
def engine():
    return VerdictEngine()


def _defect(class_name="missing", confidence=0.90):
    return {
        "class_id": 0,
        "class_name": class_name,
        "confidence": confidence,
        "x_min": 10.0, "y_min": 10.0, "x_max": 50.0, "y_max": 50.0,
    }


class TestVerdictEngine:
    def test_no_defects_is_pass(self, engine):
        result = engine.evaluate([])
        assert result.verdict == "PASS"
        assert result.severity == "NONE"
        assert result.defect_count == 0

    def test_high_conf_defect_is_fail(self, engine):
        defects = [_defect(confidence=0.95)]
        result = engine.evaluate(defects, high_conf_threshold=0.85)
        assert result.verdict == "FAIL"
        assert result.defect_count == 1
        assert len(result.flagged_defects) == 1

    def test_too_many_defects_is_fail(self, engine):
        defects = [_defect("misaligned", 0.60) for _ in range(5)]
        result = engine.evaluate(defects, max_defect_count=3)
        assert result.verdict == "FAIL"
        assert "too many" in result.reason.lower()

    def test_critical_severity_is_fail(self, engine):
        # missing → CRITICAL → FAIL even at medium confidence
        defects = [_defect("missing", confidence=0.87)]
        result = engine.evaluate(defects, high_conf_threshold=0.85)
        assert result.verdict == "FAIL"

    def test_medium_severity_low_count_is_warning(self, engine):
        # misaligned → MEDIUM → WARNING when count is small and not high-conf
        defects = [_defect("misaligned", confidence=0.60)]
        result = engine.evaluate(defects, high_conf_threshold=0.85, max_defect_count=5)
        assert result.verdict == "WARNING"

    def test_all_uncertain_is_warning(self, engine):
        defects = [_defect("scratch", confidence=0.30)]
        result = engine.evaluate(defects, warning_conf_threshold=0.50)
        assert result.verdict == "WARNING"
        assert "low confidence" in result.reason.lower()

    def test_result_is_verdict_result(self, engine):
        result = engine.evaluate([])
        assert isinstance(result, VerdictResult)
        assert hasattr(result, "verdict")
        assert hasattr(result, "severity")
        assert hasattr(result, "reason")
        assert hasattr(result, "defect_count")
        assert hasattr(result, "flagged_defects")
