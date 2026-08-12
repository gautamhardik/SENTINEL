"""
Feature Selection Policy Suite for Enterprise Fraud Detection Platform.
Decouples Feature Selection strategies (near-zero variance, multicollinearity, domain overrides) from Feature Generation.
"""
from typing import Any, Dict, List, Optional, Tuple

import polars as pl

from src.warehouse.logger import get_warehouse_logger


class FeatureSelectionPolicy:
    """
    Configurable Feature Selection Policy Engine:
    - Evaluates feature variance, preserving domain-critical fraud signals.
    - Applies configurable multicollinearity pruning rules.
    - Generates audit trace of retained vs. dropped features.
    """
    def __init__(
        self,
        near_zero_var_thresh: float = 0.00001,
        domain_critical_features: Optional[List[str]] = None,
        prune_multicollinear: bool = False
    ):
        self.near_zero_var_thresh = near_zero_var_thresh
        self.domain_critical_features = domain_critical_features or [
            "self_transfer_flag", "cross_bank_flag", "high_value_flag",
            "zero_amount_flag", "currency_mismatch_flag", "rapid_transfer_flag"
        ]
        self.prune_multicollinear = prune_multicollinear
        self.logger = get_warehouse_logger("FeatureSelectionPolicy")

    def select_features(
        self,
        df: pl.DataFrame,
        val_report: Dict[str, Any],
        registry: List[Dict[str, Any]],
        target_col: str = "is_laundering"
    ) -> Tuple[pl.DataFrame, List[Dict[str, Any]], Dict[str, Any]]:
        """
        Applies selection policy on engineered DataFrame and feature registry.
        Returns (selected_df, selected_registry, selection_summary).
        """
        self.logger.info("Executing Feature Selection Policy...")
        initial_feature_count = len(registry)
        dropped_cols = []
        selection_audit = []

        # 1. Variance Evaluation
        numeric_cols = [
            c for c in df.columns
            if c != target_col and df[c].dtype in [pl.Float32, pl.Float64, pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.UInt32, pl.UInt64]
        ]

        for col in numeric_cols:
            col_var = float((df[col].std() or 0.0) ** 2)
            if col_var < self.near_zero_var_thresh:
                if col in self.domain_critical_features:
                    selection_audit.append({
                        "feature_name": col,
                        "variance": round(col_var, 6),
                        "decision": "RETAINED",
                        "reason": "Rare but domain-critical predictive fraud signal."
                    })
                else:
                    dropped_cols.append(col)
                    selection_audit.append({
                        "feature_name": col,
                        "variance": round(col_var, 6),
                        "decision": "DROPPED",
                        "reason": f"Near-zero variance ({col_var:.6f} < {self.near_zero_var_thresh})."
                    })
            else:
                selection_audit.append({
                    "feature_name": col,
                    "variance": round(col_var, 6),
                    "decision": "RETAINED",
                    "reason": "Sufficient variance for ML modeling."
                })

        # 2. Multicollinearity Policy (Optional Pruning)
        if self.prune_multicollinear:
            high_corr_drops = val_report.get("correlation_summary", {}).get("actionable_pruning_recommendations", [])
            for col in high_corr_drops:
                if col in df.columns and col not in dropped_cols:
                    dropped_cols.append(col)
                    selection_audit.append({
                        "feature_name": col,
                        "variance": round(float((df[col].std() or 0.0) ** 2), 6),
                        "decision": "DROPPED",
                        "reason": "Multicollinearity pruning policy recommendation."
                    })

        # Apply drops to DataFrame and Registry
        df_selected = df.drop(dropped_cols) if dropped_cols else df
        selected_registry = [f for f in registry if f["feature_name"] not in dropped_cols]

        selection_summary = {
            "initial_feature_count": initial_feature_count,
            "retained_feature_count": len(selected_registry),
            "dropped_feature_count": len(dropped_cols),
            "dropped_columns": dropped_cols,
            "selection_audit": selection_audit
        }

        self.logger.info(
            f"Feature Selection complete: Retained {len(selected_registry)} / {initial_feature_count} features "
            f"(Dropped {len(dropped_cols)} features)."
        )
        return df_selected, selected_registry, selection_summary
