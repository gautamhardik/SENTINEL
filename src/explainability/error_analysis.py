"""
Error Diagnostics & Robustness Engine: Analyzes False Positives, False Negatives, high-confidence errors, systematic feature profiling, and multi-feature perturbation matrix.
"""
from typing import Any, Dict, List

import numpy as np
import polars as pl


class ErrorDiagnosticsEngine:
    """Performs confusion matrix breakdown, systematic error feature profiling (FP vs TP, FN vs TN), high-confidence error mining, and multi-feature robustness perturbation checks."""

    @staticmethod
    def categorize_errors(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.38) -> Dict[str, np.ndarray]:
        """Categorizes transaction indices into TP, TN, FP, and FN groups."""
        y_pred = (y_prob >= threshold).astype(int)

        tp_idx = np.where((y_true == 1) & (y_pred == 1))[0]
        tn_idx = np.where((y_true == 0) & (y_pred == 0))[0]
        fp_idx = np.where((y_true == 0) & (y_pred == 1))[0]
        fn_idx = np.where((y_true == 1) & (y_pred == 0))[0]

        return {
            "TP": tp_idx,
            "TN": tn_idx,
            "FP": fp_idx,
            "FN": fn_idx
        }

    @staticmethod
    def profile_error_features(X: np.ndarray, error_groups: Dict[str, np.ndarray], feature_names: List[str], top_n: int = 5) -> pl.DataFrame:
        """Profiles feature means and relative skews across FP vs TP (False Alarm vs True Fraud) and FN vs TN (Missed Fraud vs Legitimate)."""
        records = []
        for idx, fname in enumerate(feature_names):
            tp_mean = float(np.mean(X[error_groups["TP"], idx])) if len(error_groups["TP"]) > 0 else 0.0
            tn_mean = float(np.mean(X[error_groups["TN"], idx])) if len(error_groups["TN"]) > 0 else 0.0
            fp_mean = float(np.mean(X[error_groups["FP"], idx])) if len(error_groups["FP"]) > 0 else 0.0
            fn_mean = float(np.mean(X[error_groups["FN"], idx])) if len(error_groups["FN"]) > 0 else 0.0

            fp_vs_tp_skew = abs(fp_mean - tp_mean)
            fn_vs_tn_skew = abs(fn_mean - tn_mean)

            records.append({
                "feature_name": fname,
                "tp_mean": round(tp_mean, 4),
                "fp_mean": round(fp_mean, 4),
                "tn_mean": round(tn_mean, 4),
                "fn_mean": round(fn_mean, 4),
                "fp_vs_tp_skew": round(fp_vs_tp_skew, 4),
                "fn_vs_tn_skew": round(fn_vs_tn_skew, 4)
            })

        df = pl.DataFrame(records).sort("fp_vs_tp_skew", descending=True)
        return df.head(top_n)

    @staticmethod
    def analyze_high_confidence_errors(y_true: np.ndarray, y_prob: np.ndarray, fp_threshold: float = 0.80, fn_threshold: float = 0.20) -> Dict[str, List[int]]:
        """Identifies extreme misclassifications: FPs with >80% probability and FNs with <20% probability."""
        fp_high_conf = np.where((y_true == 0) & (y_prob >= fp_threshold))[0].tolist()
        fn_high_conf = np.where((y_true == 1) & (y_prob <= fn_threshold))[0].tolist()

        return {
            "high_confidence_fp": fp_high_conf,
            "high_confidence_fn": fn_high_conf
        }

    @staticmethod
    def run_robustness_perturbations(model: Any, X: np.ndarray, feature_indices: List[int], feature_names: List[str], scale_factors: List[float] = [0.90, 0.95, 1.05, 1.10, 1.25], threshold: float = 0.38) -> pl.DataFrame:
        """Tests prediction stability under multi-feature perturbations (+/- 5%, 10%, 25%)."""
        raw_model = model.estimator if hasattr(model, "estimator") else model
        base_probs = raw_model.predict_proba(X)[:, 1] if hasattr(raw_model, "predict_proba") else raw_model.predict(X)
        records = []

        for f_idx, f_name in zip(feature_indices, feature_names):
            for scale in scale_factors:
                X_pert = X.copy()
                X_pert[:, f_idx] *= scale
                pert_probs = raw_model.predict_proba(X_pert)[:, 1] if hasattr(raw_model, "predict_proba") else raw_model.predict(X_pert)

                prob_diff = np.abs(pert_probs - base_probs)
                flips = int(np.sum((base_probs >= threshold) != (pert_probs >= threshold)))

                records.append({
                    "feature_name": f_name,
                    "scale_factor": scale,
                    "mean_abs_prob_shift": round(float(np.mean(prob_diff)), 4),
                    "max_abs_prob_shift": round(float(np.max(prob_diff)), 4),
                    "decision_flips": flips,
                    "flip_rate_pct": round((flips / len(X)) * 100.0, 2)
                })

        return pl.DataFrame(records)
