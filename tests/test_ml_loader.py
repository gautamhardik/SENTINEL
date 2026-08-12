"""
Unit tests for FeatureValidator in fraud_detection.validation.
"""
import pandas as pd

from fraud_detection.validation import FeatureValidator


def test_feature_validator():
    raw_features = ["Amount_Paid", "From_Account", "To_Account"]
    validator = FeatureValidator(raw_features=raw_features)

    df_valid = pd.DataFrame([{
        "Amount_Paid": 500.0,
        "From_Account": "ACC-101",
        "To_Account": "ACC-202"
    }])
    result = validator.validate(df_valid)
    assert result.is_valid is True
    assert len(result.errors) == 0

    df_invalid = pd.DataFrame([{"Amount_Paid": 500.0}])
    result_invalid = validator.validate(df_invalid)
    assert result_invalid.is_valid is False
    assert len(result_invalid.errors) > 0
