"""
SHAP Analysis Engine: TreeExplainer initialization, global importance, feature ranking, dependence values, and stability analysis.
"""
from typing import Any, List

import numpy as np
import polars as pl
import shap


class SHAPAnalysisEngine:
    """Computes SHAP values, feature importance rankings, dependence values, and stability metrics using TreeExplainer."""

    def __init__(self, model: Any):
        # Unwrap FrozenEstimator or CalibratedClassifierCV if wrapped
        raw = model
        if hasattr(raw, "estimator"):
            raw = raw.estimator
        if hasattr(raw, "estimator"):
            raw = raw.estimator
        if hasattr(raw, "raw_model"):
            raw = raw.raw_model

        self.raw_model = raw
        self.explainer = shap.TreeExplainer(self.raw_model)

    def compute_shap_values(self, X: np.ndarray) -> np.ndarray:
        """Computes raw SHAP values for given dataset array."""
        shap_vals = self.explainer.shap_values(X)
        if isinstance(shap_vals, list):
            # For binary classification return positive class SHAP values
            return shap_vals[1]
        return shap_vals

    def get_base_value(self) -> float:
        """Returns base value (expected value) of model output."""
        ev = getattr(self.explainer, "expected_value", 0.0)
        if isinstance(ev, (list, np.ndarray)):
            return float(ev[1]) if len(ev) > 1 else float(ev[0])
        return float(ev)

    def get_global_importance(self, shap_values: np.ndarray, feature_names: List[str]) -> pl.DataFrame:
        """Calculates mean absolute SHAP importance per feature, cumulative percentage, and ranks them."""
        mean_abs_shap = np.mean(np.abs(shap_values), axis=0)
        total_shap = np.sum(mean_abs_shap) if np.sum(mean_abs_shap) > 0 else 1.0

        df = pl.DataFrame({
            "feature_name": feature_names,
            "mean_abs_shap": mean_abs_shap,
            "pct_importance": (mean_abs_shap / total_shap) * 100.0
        }).sort("mean_abs_shap", descending=True)

        cum_pct = np.cumsum(df["pct_importance"].to_numpy())
        df = df.with_columns(pl.Series("cumulative_pct", cum_pct))
        return df

    def compute_shap_stability(self, X: np.ndarray, feature_names: List[str], n_bootstrap: int = 10, sample_ratio: float = 0.8, seed: int = 42) -> pl.DataFrame:
        """Evaluates SHAP feature ranking stability across bootstrap samples."""
        np.random.seed(seed)
        n_samples = int(len(X) * sample_ratio)
        rankings = []

        for b in range(n_bootstrap):
            idx = np.random.choice(len(X), size=n_samples, replace=True)
            shap_b = self.compute_shap_values(X[idx])
            imp_b = np.mean(np.abs(shap_b), axis=0)
            # Rank (1 = highest importance)
            rank_b = len(feature_names) - np.argsort(np.argsort(imp_b))
            rankings.append(rank_b)

        rankings_arr = np.array(rankings) # (n_bootstrap, n_features)
        mean_ranks = np.mean(rankings_arr, axis=0)
        std_ranks = np.std(rankings_arr, axis=0)

        df = pl.DataFrame({
            "feature_name": feature_names,
            "mean_rank": mean_ranks,
            "std_rank": std_ranks
        }).sort("mean_rank", descending=False)

        return df
