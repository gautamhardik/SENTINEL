"""
Unit tests for FeatureValidator.
"""
import pandas as pd

from fraud_detection.validation import FeatureValidator


def test_validator_valid_payload():
    raw_cols = ["Amount_Paid", "Amount_Received", "is_amount_outlier"]
    validator = FeatureValidator(raw_features=raw_cols)

    df = pd.DataFrame([{"Amount_Paid": 100.0, "Amount_Received": 100.0, "is_amount_outlier": 0}])
    res = validator.validate(df)
    assert res.is_valid is True
    assert len(res.errors) == 0


def test_validator_missing_columns():
    raw_cols = ["Amount_Paid", "Amount_Received", "is_amount_outlier"]
    validator = FeatureValidator(raw_features=raw_cols)

    df = pd.DataFrame([{"Amount_Paid": 100.0}])
    res = validator.validate(df)
    assert res.is_valid is False
    assert len(res.errors) == 1
    assert "Missing 2 required feature columns" in res.errors[0]
