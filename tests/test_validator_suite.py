"""
Dedicated Validator & Quality Scorecard Test Suite for Enterprise Fraud Detection Platform.
Tests Schema Validation, Phi Coefficient, Quality Score (0-100), Registry Audit, and Baseline Exports.
"""
from datetime import datetime, timedelta

import polars as pl
import pytest

from src.features.validator import FeatureValidator


@pytest.fixture
def sample_feature_df() -> pl.DataFrame:
    base_time = datetime(2026, 1, 1, 10, 0, 0)
    data = [
        {
            "Timestamp": base_time, "amount_paid": 100.0, "self_transfer_flag": 1,
            "cross_bank_flag": 0, "rapid_transfer_flag": 0, "is_laundering": 0
        },
        {
            "Timestamp": base_time + timedelta(minutes=1), "amount_paid": 500.0, "self_transfer_flag": 0,
            "cross_bank_flag": 1, "rapid_transfer_flag": 1, "is_laundering": 1
        },
        {
            "Timestamp": base_time + timedelta(minutes=5), "amount_paid": 1000.0, "self_transfer_flag": 1,
            "cross_bank_flag": 0, "rapid_transfer_flag": 0, "is_laundering": 0
        }
    ]
    df = pl.DataFrame(data)
    return df.with_columns([
        pl.col("Timestamp").cast(pl.Datetime),
        pl.col("amount_paid").cast(pl.Float64),
        pl.col("self_transfer_flag").cast(pl.Int32),
        pl.col("cross_bank_flag").cast(pl.Int32),
        pl.col("rapid_transfer_flag").cast(pl.Int32),
        pl.col("is_laundering").cast(pl.Int32)
    ])


@pytest.fixture
def sample_registry() -> list:
    return [
        {
            "feature_name": "amount_paid", "category": "Transaction", "stage": "Stage 1",
            "data_type": "Float64", "availability": "online", "requires_historical_labels": False,
            "depends_on": ["Amount_Paid"], "transformation_rule": "identity", "description": "Raw amount paid."
        },
        {
            "feature_name": "self_transfer_flag", "category": "Transaction", "stage": "Stage 1",
            "data_type": "Int32", "availability": "online", "requires_historical_labels": False,
            "depends_on": ["From_Account", "To_Account"], "transformation_rule": "equality", "description": "Flag self transfer."
        }
    ]


def test_validator_schema_validation(sample_feature_df, sample_registry):
    validator = FeatureValidator()

    # Valid schema
    res = validator.validate_schema(sample_feature_df, sample_registry)
    assert res["status"] == "PASSED"
    assert len(res["missing_columns"]) == 0

    # Schema with missing registered feature
    bad_registry = sample_registry + [{
        "feature_name": "non_existent_col", "data_type": "Float64"
    }]
    res_bad = validator.validate_schema(sample_feature_df, bad_registry)
    assert res_bad["status"] == "WARNING"
    assert "non_existent_col" in res_bad["missing_columns"]


def test_validator_phi_coefficient(sample_feature_df):
    validator = FeatureValidator()
    # Compute phi for self_transfer_flag and cross_bank_flag (perfect negative association)
    phi_val = validator._compute_phi_coefficient(sample_feature_df["self_transfer_flag"], sample_feature_df["cross_bank_flag"])
    assert abs(phi_val) == 1.0


def test_validator_feature_quality_score(sample_feature_df, sample_registry):
    validator = FeatureValidator()
    report = validator.validate(sample_feature_df, registry=sample_registry)

    assert "feature_quality_score" in report
    assert 0.0 <= report["feature_quality_score"] <= 100.0


def test_validator_registry_audit(sample_registry):
    validator = FeatureValidator()

    res = validator.validate_registry(sample_registry)
    assert res["registry_status"] == "PASSED"

    # Bad registry with unflagged target dependency
    bad_reg = sample_registry + [{
        "feature_name": "bad_target_feature", "description": "test", "availability": "online",
        "depends_on": ["is_laundering"], "requires_historical_labels": False
    }]
    res_bad = validator.validate_registry(bad_reg)
    assert res_bad["registry_status"] == "FAILED"
    assert "bad_target_feature" in res_bad["unflagged_target_dependencies"]


def test_validator_temporal_ordering_assertion(sample_feature_df):
    validator = FeatureValidator()

    report = validator.validate(sample_feature_df)
    assert report["temporal_ordering_verified"] is True

    # Unsorted dataframe should fail temporal check
    unsorted_df = sample_feature_df.sort("Timestamp", descending=True)
    report_unsorted = validator.validate(unsorted_df)
    assert report_unsorted["temporal_ordering_verified"] is False
    assert report_unsorted["validation_status"] == "FAILED"
