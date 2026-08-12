"""
Threshold Engine Module categorizing calibrated probabilities into business RiskLevels.
"""
from fraud_detection.core import BaseThresholdEngine, RiskLevel, RiskResult


class ThresholdEngine(BaseThresholdEngine):
    """Maps calibrated fraud probabilities to business decision boundaries and RiskLevel tiers."""

    def __init__(self, optimal_threshold: float = 0.26):
        self.optimal_threshold = optimal_threshold

    def evaluate(self, calibrated_prob: float) -> RiskResult:
        prob = float(calibrated_prob)

        if prob >= 0.75:
            risk = RiskLevel.CRITICAL
            decision = "FLAGGED_CRITICAL_FRAUD"
            action = "IMMEDIATE_BLOCK_AND_FREEZE"
            reason = f"Extreme fraud probability ({prob:.1%}) exceeds critical 75% boundary."
        elif prob >= self.optimal_threshold:
            risk = RiskLevel.HIGH
            decision = "FLAGGED_FRAUD"
            action = "HOLD_FOR_MANUAL_INVESTIGATION"
            reason = f"Calibrated fraud probability ({prob:.1%}) exceeds optimal business threshold ({self.optimal_threshold:.2f})."
        elif prob >= 0.10:
            risk = RiskLevel.MEDIUM
            decision = "APPROVED_WITH_MONITORING"
            action = "AUTO_APPROVE_STEP_UP_AUTH"
            reason = f"Moderate fraud probability ({prob:.1%}); requires step-up authentication check."
        else:
            risk = RiskLevel.LOW
            decision = "APPROVED_LEGITIMATE"
            action = "AUTO_APPROVE"
            reason = f"Low fraud probability ({prob:.1%}); clean transaction."

        return RiskResult(
            decision=decision,
            risk_level=risk,
            threshold=self.optimal_threshold,
            action=action,
            trigger_reason=reason
        )
