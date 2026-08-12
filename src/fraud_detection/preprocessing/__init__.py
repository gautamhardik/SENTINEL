"""
Production Preprocessor Pipeline Module encapsulating Scikit-Learn ColumnTransformers.
"""
from typing import Any, List

import numpy as np
import pandas as pd

from fraud_detection.exceptions import PredictionEngineError


class ProductionPreprocessor:
    """Transforms raw transaction DataFrames into ordered, scaled feature vectors."""

    def __init__(self, preprocessor_binary: Any, raw_features: List[str], feature_order: List[str]):
        self.pipeline = preprocessor_binary
        self.raw_features = list(raw_features)
        self.feature_order = list(feature_order)
        if hasattr(self.pipeline, "feature_names_in_"):
            self._expected_names = list(self.pipeline.feature_names_in_)
        else:
            self._expected_names = list(self.feature_order)

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        try:
            local_df = df.copy()
            df_cols = set(local_df.columns)

            # If columns are prefixed with numeric__, strip prefix if needed
            if not any(c in df_cols for c in self._expected_names):
                rename_map = {c: c.replace("numeric__", "") for c in local_df.columns if c.startswith("numeric__")}
                if rename_map:
                    local_df = local_df.rename(columns=rename_map)

            # Select expected feature columns strictly
            missing = [c for c in self._expected_names if c not in local_df.columns]
            for col in missing:
                local_df[col] = 0.0

            sub_df = local_df[self._expected_names].copy()

            if hasattr(self.pipeline, "transform"):
                X_trans = self.pipeline.transform(sub_df)
                if hasattr(X_trans, "toarray"):
                    X_trans = X_trans.toarray()
            else:
                X_trans = sub_df.to_numpy(dtype=np.float64)

            if X_trans.shape[1] != len(self.feature_order):
                raise PredictionEngineError(
                    f"Transformed feature dimension ({X_trans.shape[1]}) does not match expected ({len(self.feature_order)})."
                )
            return X_trans
        except Exception as e:
            raise PredictionEngineError(f"Error during production preprocessing transformation: {str(e)}")
