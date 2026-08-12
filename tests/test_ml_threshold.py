"""
Unit tests for ThresholdEngine in fraud_detection.thresholding.
"""
from fraud_detection.core import RiskLevel
from fraud_detection.thresholding import ThresholdEngine


def test_threshold_engine():
    engine = ThresholdEngine(optimal_threshold=0.26)

    res_low = engine.evaluate(0.05)
    assert res_low.risk_level == RiskLevel.LOW
    assert res_low.action == "AUTO_APPROVE"

    res_med = engine.evaluate(0.15)
    assert res_med.risk_level == RiskLevel.MEDIUM

    res_high = engine.evaluate(0.30)
    assert res_high.risk_level == RiskLevel.HIGH

    res_crit = engine.evaluate(0.85)
    assert res_crit.risk_level == RiskLevel.CRITICAL
