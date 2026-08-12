"""
Business-Friendly Explainability Engine Module converting feature attributions into plain-English analyst cards.
"""
from typing import Any, Dict, List

import numpy as np
import shap

from fraud_detection.core import BaseExplainer, BusinessExplanation, RiskLevel


def _extract_raw_tree_model(model: Any) -> Any:
    """Unwraps scikit-learn CalibratedClassifierCV, FrozenEstimator, or Pipeline wrappers down to base GBDT model."""
    curr = model
    while True:
        if hasattr(curr, "estimator"):
            curr = curr.estimator
        elif hasattr(curr, "base_estimator"):
            curr = curr.base_estimator
        elif hasattr(curr, "estimator_"):
            curr = curr.estimator_
        else:
            break
    return curr


class ExplainabilityEngine(BaseExplainer):
    """Generates human-readable business explanations and actionable recourse without raw plot overhead."""

    def __init__(self, raw_model: Any, feature_order: List[str]):
        base_gbdt = _extract_raw_tree_model(raw_model)
        self.feature_order = feature_order
        self.explainer = shap.TreeExplainer(base_gbdt)

    def explain(self, sample_row: np.ndarray, shap_row: np.ndarray, proba: float, threshold: float) -> BusinessExplanation:
        sorted_idx = np.argsort(np.abs(shap_row))[::-1]

        top_risk_drivers = []
        for idx in sorted_idx:
            sval = float(shap_row[idx])
            if sval > 0 and len(top_risk_drivers) < 4:
                fname = self.feature_order[idx]
                fval = float(sample_row[idx])
                top_risk_drivers.append({
                    "feature": fname,
                    "value": round(fval, 4),
                    "shap_impact": round(sval, 4)
                })

        # Counterfactual advice
        recommends = []
        pos_idx = np.where(shap_row > 0)[0]
        sorted_pos = pos_idx[np.argsort(shap_row[pos_idx])[::-1]]

        for idx in sorted_pos[:2]:
            fname = self.feature_order[idx]
            orig_val = float(sample_row[idx])
            sval = float(shap_row[idx])
            sug_val = orig_val * 0.50 if orig_val != 0 else -1.0

            recommends.append({
                "feature": fname,
                "current_value": round(orig_val, 4),
                "suggested_value": round(sug_val, 4),
                "estimated_shap_reduction": round(sval * 0.50, 4)
            })

        # Card rendering
        risk_level = "🚨 HIGH RISK" if proba >= 0.75 else ("⚠️ MEDIUM RISK" if proba >= threshold else "✅ LOW RISK")
        action = "HOLD & MANUAL INVESTIGATION" if proba >= threshold else "AUTO-APPROVE"

        card = f"""### 🛡️ Fraud Investigator Decision Card

| Metric | Value |
| :--- | :--- |
| **Fraud Probability** | `{proba:.2%}` ({risk_level}) |
| **Decision Boundary** | `{threshold:.2f}` |
| **System Action** | **{action}** |

#### 🔑 Key Risk Indicators:
"""
        for d in top_risk_drivers[:3]:
            card += f"- **{d['feature']}** = `{d['value']}` (Risk Contribution: `+{d['shap_impact']}`)\n"

        return BusinessExplanation(
            investigator_card=card,
            top_risk_drivers=top_risk_drivers,
            counterfactual_advice=recommends
        )
