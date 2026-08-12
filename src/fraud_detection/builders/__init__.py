"""
PredictionResponse Builders Module assembling structured typed outputs.
"""
import time
from typing import Any, Dict, List

from fraud_detection.core import BusinessExplanation, PredictionContext, PredictionSession, RiskResult


class PredictionBuilder:
    """Assembles typed PredictionSession objects from pipeline outputs."""

    @staticmethod
    def build_session(
        context: PredictionContext,
        risk_res: RiskResult,
        raw_prob: float,
        cal_prob: float,
        explanation: BusinessExplanation,
        total_latency: float,
        stage_latencies: Dict[str, float]
    ) -> PredictionSession:
        return PredictionSession(
            request_id=context.request_id,
            decision=risk_res.decision,
            risk_level=risk_res.risk_level,
            raw_probability=round(float(raw_prob), 4),
            calibrated_probability=round(float(cal_prob), 4),
            threshold=risk_res.threshold,
            top_risk_drivers=explanation.top_risk_drivers,
            counterfactual_advice=explanation.counterfactual_advice,
            investigator_card=explanation.investigator_card,
            model_version=context.model_version,
            total_latency_ms=round(total_latency, 4),
            stage_latencies_ms=stage_latencies,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
        )
