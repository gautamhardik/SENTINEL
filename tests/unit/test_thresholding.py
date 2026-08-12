"""
Unit tests for ThresholdEngine and RiskLevel classification.
"""
from fraud_detection.core import RiskLevel
from fraud_detection.thresholding import ThresholdEngine


def test_threshold_classification():
    engine = ThresholdEngine(optimal_threshold=0.26)

    # Low Risk
    res_low = engine.evaluate(0.05)
    assert res_low.risk_level == RiskLevel.LOW
    assert res_low.decision == "APPROVED_LEGITIMATE"

    # Medium Risk
    res_med = engine.evaluate(0.15)
    assert res_med.risk_level == RiskLevel.MEDIUM
    assert res_med.decision == "APPROVED_WITH_MONITORING"

    # High Risk (Threshold Breach)
    res_high = engine.evaluate(0.35)
    assert res_high.risk_level == RiskLevel.HIGH
    assert res_high.decision == "FLAGGED_FRAUD"

    # Critical Risk
    res_crit = engine.evaluate(0.85)
    assert res_crit.risk_level == RiskLevel.CRITICAL
    assert res_crit.decision == "FLAGGED_CRITICAL_FRAUD"
