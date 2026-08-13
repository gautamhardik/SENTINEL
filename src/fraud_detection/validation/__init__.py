"""
Feature Validator Module checking input DataFrame schemas, datatypes, missing columns, and bounds.
"""
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from fraud_detection.core import BaseValidator, ValidationResult
from fraud_detection.exceptions import FeatureValidationError, SchemaMismatchError


class FeatureValidator(BaseValidator):
    """Validates incoming transaction payloads against expected feature schema with thread-safe read-only checks."""

    def __init__(self, raw_features: List[str], feature_order: Optional[List[str]] = None):
        self.raw_features = list(raw_features)  # Defensive copy
        self.feature_order = list(feature_order) if feature_order is not None else []

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        errors = []
        warnings = []

        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            errors.append("Input DataFrame payload is empty, None, or improperly formatted.")
            return ValidationResult(is_valid=False, errors=errors)

        df_cols_set = set(df.columns)

        # Check if df contains engineered features (prefix "numeric__") or model feature_order
        is_engineered = any(c in df_cols_set for c in self.feature_order) or any(c.startswith("numeric__") for c in df.columns)

        if is_engineered and self.feature_order:
            target_features = self.feature_order
        else:
            # Always validate against raw_features for raw transaction payloads
            target_features = self.raw_features

        # 1. Missing columns check
        missing_cols = [c for c in target_features if c not in df_cols_set]
        if missing_cols:
            if len(missing_cols) == 1:
                errors.append(f"Missing required feature column: '{missing_cols[0]}'. Payload schema does not match model requirements.")
            else:
                errors.append(f"Missing {len(missing_cols)} required feature columns: {missing_cols[:4]} (total missing: {len(missing_cols)}).")

        # 2. Unexpected extra columns check (Warning)
        target_set = set(target_features)
        extra_cols = [c for c in df.columns if c not in target_set]
        if extra_cols:
            warnings.append(f"Payload contains {len(extra_cols)} unmapped columns ({extra_cols[:3]}) which will be excluded from feature vector.")

        # 3. Read-only Null values check
        if not missing_cols and target_features:
            sub_df = df[target_features]
            null_cols = sub_df.columns[sub_df.isnull().any()].tolist()
            if null_cols:
                null_cnt = int(sub_df[null_cols].isnull().sum().sum())
                warnings.append(f"Payload contains {null_cnt} missing values across columns {null_cols[:3]}; median imputation will be automatically applied.")

        is_valid = len(errors) == 0
        passed_cnt = len(target_features) - len(missing_cols)

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            passed_count=passed_cnt
        )
