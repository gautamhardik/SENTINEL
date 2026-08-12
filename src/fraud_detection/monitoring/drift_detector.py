"""
Feature Drift & Population Stability Index (PSI) Detector Module
Provides real-time and batch drift monitoring for production fraud features.
"""

from typing import Any, Dict, List

import numpy as np


class DriftDetector:
    def __init__(self, num_buckets: int = 10):
        self.num_buckets = num_buckets

    def calculate_psi(self, baseline: np.ndarray, current: np.ndarray) -> float:
        """
        Calculate Population Stability Index (PSI) between baseline (reference) and current distributions.
        PSI < 0.1: No significant distribution change.
        0.1 <= PSI < 0.2: Moderate distribution shift (monitoring recommended).
        PSI >= 0.2: Significant distribution shift (model retraining required).
        """
        baseline = np.asarray(baseline, dtype=float)
        current = np.asarray(current, dtype=float)

        if len(baseline) == 0 or len(current) == 0:
            return 0.0

        percentiles = np.linspace(0, 100, self.num_buckets + 1)
        buckets = np.percentile(baseline, percentiles)
        buckets[0] -= 1e-5
        buckets[-1] += 1e-5

        baseline_counts, _ = np.histogram(baseline, bins=buckets)
        current_counts, _ = np.histogram(current, bins=buckets)

        baseline_pct = baseline_counts / len(baseline)
        current_pct = current_counts / len(current)

        eps = 1e-4
        baseline_pct = np.where(baseline_pct == 0, eps, baseline_pct)
        current_pct = np.where(current_pct == 0, eps, current_pct)

        psi_val = np.sum((current_pct - baseline_pct) * np.log(current_pct / baseline_pct))
        return float(psi_val)

    def evaluate_feature_drift(
        self, baseline_data: Dict[str, List[float]], current_data: Dict[str, List[float]]
    ) -> Dict[str, Any]:
        """Evaluate drift across a dictionary of baseline and current feature vectors."""
        results = {}
        overall_drift_alert = False

        for feature_name, baseline_vals in baseline_data.items():
            if feature_name in current_data:
                curr_vals = current_data[feature_name]
                psi = self.calculate_psi(np.array(baseline_vals), np.array(curr_vals))

                status = "STABLE"
                if psi >= 0.2:
                    status = "HIGH_DRIFT"
                    overall_drift_alert = True
                elif psi >= 0.1:
                    status = "MODERATE_DRIFT"

                results[feature_name] = {
                    "psi": round(psi, 4),
                    "status": status
                }

        return {
            "overall_drift_alert": overall_drift_alert,
            "feature_metrics": results
        }

drift_detector = DriftDetector()
