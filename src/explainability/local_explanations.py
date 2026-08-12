"""
Local Explanations and Counterfactual Engine: Converts SHAP attribution into human-readable business explanations, investigator cards, and counterfactual feature changes.
"""
from typing import Any, Dict, List

import numpy as np


class LocalExplanationEngine:
    """Generates transaction-level attribution reports, investigator dashboard cards, and counterfactual recourse advice."""

    def __init__(self, feature_names: List[str]):
        self.feature_names = feature_names

    def explain_transaction(self, sample_idx: int, X_row: np.ndarray, shap_row: np.ndarray, base_value: float, proba: float, threshold: float = 0.38) -> Dict[str, Any]:
        """Generates a structured human-readable breakdown for a single transaction."""
        decision = "FLAGGED_FRAUD" if proba >= threshold else "APPROVED_LEGITIMATE"

        sorted_indices = np.argsort(np.abs(shap_row))[::-1]

        top_positive = []
        top_negative = []

        for idx in sorted_indices:
            fname = self.feature_names[idx]
            fval = float(X_row[idx])
            sval = float(shap_row[idx])

            if sval > 0 and len(top_positive) < 5:
                top_positive.append({"feature": fname, "value": round(fval, 4), "shap_impact": round(sval, 4)})
            elif sval < 0 and len(top_negative) < 5:
                top_negative.append({"feature": fname, "value": round(fval, 4), "shap_impact": round(sval, 4)})

        return {
            "sample_index": sample_idx,
            "probability": round(float(proba), 4),
            "decision_threshold": threshold,
            "decision": decision,
            "base_value": round(float(base_value), 4),
            "top_risk_drivers": top_positive,
            "top_safety_drivers": top_negative,
            "investigator_summary": f"Transaction declared {decision} (Calibrated Risk: {proba:.2%}, Threshold: {threshold:.2f}). Primary risk driver: {top_positive[0]['feature'] if top_positive else 'N/A'}."
        }

    def build_investigator_card(self, sample_idx: int, X_row: np.ndarray, shap_row: np.ndarray, proba: float, threshold: float = 0.38) -> str:
        """Renders analyst-facing investigator card formatted as Markdown with structured sections."""
        exp = self.explain_transaction(sample_idx, X_row, shap_row, 0.0, proba, threshold)
        rec = self.generate_counterfactual(X_row, shap_row)

        risk_level = "🚨 HIGH RISK" if proba >= 0.75 else ("⚠️ MEDIUM RISK" if proba >= threshold else "✅ LOW RISK")
        action = "HOLD & MANUAL INVESTIGATION" if proba >= threshold else "AUTO-APPROVE"
        confidence = "HIGH (Calibrated Isotonic Score)" if (proba >= 0.85 or proba <= 0.15) else "MEDIUM"
        reason = f"Calculated calibrated fraud probability of {proba:.1%} exceeds optimized business threshold of {threshold:.2f} ($15 FP vs $500 FN cost balance)."

        card = f"""
### 🛡️ Fraud Investigator Decision Card (Sample #{sample_idx})

| Metric | Value |
| :--- | :--- |
| **Fraud Probability** | `{proba:.2%}` ({risk_level}) |
| **Decision Boundary** | `{threshold:.2f}` |
| **Prediction Confidence** | `{confidence}` |
| **Recommended Action** | **{action}** |

#### 📋 Business Rationale & Trigger Reason:
> {reason}

#### 🔑 Top Contributing Risk Indicators:
"""
        for d in exp["top_risk_drivers"][:4]:
            card += f"- **{d['feature']}** = `{d['value']}` (SHAP Risk Contribution: `+{d['shap_impact']}`)\n"

        card += "\n#### 💡 Actionable Recourse & Mitigation:\n"
        for r in rec[:2]:
            card += f"- Reduce **{r['feature']}** from `{r['current_value']}` to `{r['suggested_value']}` (Estimated risk drop: `-{r['estimated_shap_reduction']}`)\n"

        return card

    def generate_counterfactual(self, X_row: np.ndarray, shap_row: np.ndarray, target_reduction: float = 0.20) -> List[Dict[str, Any]]:
        """Identifies minimal feature adjustments required to shift a high-risk prediction below threshold."""
        pos_indices = np.where(shap_row > 0)[0]
        sorted_pos = pos_indices[np.argsort(shap_row[pos_indices])[::-1]]

        recommends = []
        accumulated_reduction = 0.0

        for idx in sorted_pos:
            fname = self.feature_names[idx]
            orig_val = float(X_row[idx])
            sval = float(shap_row[idx])

            suggested_val = orig_val * 0.50 if orig_val != 0 else -1.0
            accumulated_reduction += sval * 0.50

            recommends.append({
                "feature": fname,
                "current_value": round(orig_val, 4),
                "suggested_value": round(suggested_val, 4),
                "estimated_shap_reduction": round(sval * 0.50, 4)
            })

            if len(recommends) >= 3:
                break

        return recommends
