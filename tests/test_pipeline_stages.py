"""
Comprehensive Stage-by-Stage Modular Unit Tests for Phase 4 Enterprise Feature Pipeline.
Verifies temporal ordering, zero leakage semantics (shift 1), data types, and selection policy.
"""
from datetime import datetime, timedelta

import polars as pl
import pytest

from src.features.feature_engineer import FeatureEngineer
from src.features.selector import FeatureSelectionPolicy
from src.features.validator import FeatureValidator


@pytest.fixture
def dummy_transactions() -> pl.DataFrame:
    """Generates synthetic temporal transactions dataframe for multi-account testing."""
    base_time = datetime(2026, 1, 1, 10, 0, 0)
    data = [
        # Account A transactions
        {
            "transaction_key": 1, "transaction_id": "T1", "time_key": 1, "Timestamp": base_time,
            "from_bank_key": 1, "From_Bank": "BankA", "from_account_key": 101, "From_Account": "AccA",
            "to_bank_key": 2, "To_Bank": "BankB", "to_account_key": 201, "To_Account": "AccB",
            "payment_format_key": 1, "Payment_Format": "ACH", "payment_currency_key": 1, "Payment_Currency": "USD",
            "receiving_currency_key": 1, "Receiving_Currency": "USD", "Amount_Paid": 100.0, "Amount_Received": 100.0,
            "is_amount_outlier": 0, "is_laundering": 0
        },
        {
            "transaction_key": 2, "transaction_id": "T2", "time_key": 2, "Timestamp": base_time + timedelta(minutes=2),
            "from_bank_key": 1, "From_Bank": "BankA", "from_account_key": 101, "From_Account": "AccA",
            "to_bank_key": 2, "To_Bank": "BankB", "to_account_key": 202, "To_Account": "AccC",
            "payment_format_key": 1, "Payment_Format": "ACH", "payment_currency_key": 1, "Payment_Currency": "USD",
            "receiving_currency_key": 1, "Receiving_Currency": "USD", "Amount_Paid": 500.0, "Amount_Received": 500.0,
            "is_amount_outlier": 0, "is_laundering": 1
        },
        {
            "transaction_key": 3, "transaction_id": "T3", "time_key": 3, "Timestamp": base_time + timedelta(minutes=10),
            "from_bank_key": 1, "From_Bank": "BankA", "from_account_key": 101, "From_Account": "AccA",
            "to_bank_key": 2, "To_Bank": "BankB", "to_account_key": 201, "To_Account": "AccB",
            "payment_format_key": 1, "Payment_Format": "ACH", "payment_currency_key": 1, "Payment_Currency": "USD",
            "receiving_currency_key": 1, "Receiving_Currency": "USD", "Amount_Paid": 1000.0, "Amount_Received": 1000.0,
            "is_amount_outlier": 0, "is_laundering": 0
        },
        # Account B transactions
        {
            "transaction_key": 4, "transaction_id": "T4", "time_key": 4, "Timestamp": base_time + timedelta(minutes=15),
            "from_bank_key": 2, "From_Bank": "BankB", "from_account_key": 102, "From_Account": "AccX",
            "to_bank_key": 1, "To_Bank": "BankA", "to_account_key": 101, "To_Account": "AccA",
            "payment_format_key": 2, "Payment_Format": "Wire", "payment_currency_key": 1, "Payment_Currency": "USD",
            "receiving_currency_key": 2, "Receiving_Currency": "EUR", "Amount_Paid": 0.0, "Amount_Received": 0.0,
            "is_amount_outlier": 0, "is_laundering": 0
        }
    ]
    df = pl.DataFrame(data)
    return df.with_columns([
        pl.col("Timestamp").cast(pl.Datetime),
        pl.col("Amount_Paid").cast(pl.Float64),
        pl.col("Amount_Received").cast(pl.Float64)
    ])


def test_stage1_transaction_features(dummy_transactions):
    engineer = FeatureEngineer()
    df_feat = engineer.build_feature_store(dummy_transactions)

    expected_cols = [
        "amount_paid", "amount_received", "amount_difference", "amount_ratio",
        "log_amount", "self_transfer_flag", "cross_bank_flag", "high_value_flag",
        "zero_amount_flag", "currency_mismatch_flag", "payment_format_encoded"
    ]
    for col in expected_cols:
        assert col in df_feat.columns

    # Verify logic
    assert df_feat["amount_difference"][0] == 0.0
    assert df_feat["cross_bank_flag"][0] == 1
    assert df_feat["zero_amount_flag"][3] == 1


def test_stage2_temporal_features(dummy_transactions):
    engineer = FeatureEngineer()
    df_feat = engineer.build_feature_store(dummy_transactions)

    expected_cols = ["hour", "weekday", "month", "quarter", "weekend_flag", "sin_hour", "cos_hour"]
    for col in expected_cols:
        assert col in df_feat.columns

    assert df_feat["hour"][0] == 10
    assert df_feat["weekday"][0] == 4  # Thursday


def test_stage3_behavioral_features_leak_free(dummy_transactions):
    """Verifies that for transaction 0 of an account, prior historical counters are strictly 0 (no leakage)."""
    engineer = FeatureEngineer()
    df_feat = engineer.build_feature_store(dummy_transactions)

    # First transaction for AccA (Row 0)
    assert df_feat.filter(pl.col("From_Account") == "AccA")["account_transaction_count"][0] == 0
    assert df_feat.filter(pl.col("From_Account") == "AccA")["account_total_paid"][0] == 0.0

    # Second transaction for AccA (Row 1): prior count must be 1, prior total paid must be 100.0
    acc_a_df = df_feat.filter(pl.col("From_Account") == "AccA")
    assert acc_a_df["account_transaction_count"][1] == 1
    assert acc_a_df["account_total_paid"][1] == 100.0

    # Third transaction for AccA (Row 2): prior count must be 2, prior total paid must be 600.0
    assert acc_a_df["account_transaction_count"][2] == 2
    assert acc_a_df["account_total_paid"][2] == 600.0


def test_stage4_velocity_features(dummy_transactions):
    engineer = FeatureEngineer()
    df_feat = engineer.build_feature_store(dummy_transactions)

    acc_a_df = df_feat.filter(pl.col("From_Account") == "AccA")
    # First transaction: seconds_since_last_tx should be default 999999.0
    assert acc_a_df["seconds_since_last_tx"][0] == 999999.0

    # Second transaction: 2 minutes after first = 120 seconds
    assert acc_a_df["seconds_since_last_tx"][1] == 120.0
    assert acc_a_df["rapid_transfer_flag"][1] == 1


def test_stage5_statistical_features_expanding(dummy_transactions):
    engineer = FeatureEngineer()
    df_feat = engineer.build_feature_store(dummy_transactions)

    assert "amount_zscore" in df_feat.columns
    assert "account_std" in df_feat.columns
    assert "coefficient_of_variation" in df_feat.columns


def test_stage6_risk_features(dummy_transactions):
    engineer = FeatureEngineer()
    df_feat = engineer.build_feature_store(dummy_transactions)

    assert "bank_fraud_rate" in df_feat.columns
    assert "payment_format_risk" in df_feat.columns
    assert "currency_risk" in df_feat.columns


def test_stage7_network_features(dummy_transactions):
    engineer = FeatureEngineer()
    df_feat = engineer.build_feature_store(dummy_transactions)

    assert "sender_out_degree" in df_feat.columns
    assert "receiver_in_degree" in df_feat.columns
    assert "unique_counterparties" in df_feat.columns


def test_stage8_rolling_features_shift(dummy_transactions):
    """Verifies that rolling windows use prior transactions (shifted by 1)."""
    engineer = FeatureEngineer()
    df_feat = engineer.build_feature_store(dummy_transactions)

    acc_a_df = df_feat.filter(pl.col("From_Account") == "AccA")
    # Transaction 0: lag_amount_1 must be 0.0
    assert acc_a_df["lag_amount_1"][0] == 0.0
    # Transaction 1: lag_amount_1 must be 100.0 (the amount of transaction 0)
    assert acc_a_df["lag_amount_1"][1] == 100.0


def test_feature_selection_policy(dummy_transactions):
    engineer = FeatureEngineer()
    df_feat = engineer.build_feature_store(dummy_transactions)

    validator = FeatureValidator()
    val_report = validator.validate(df_feat)

    policy = FeatureSelectionPolicy(near_zero_var_thresh=0.00001)
    df_sel, sel_reg, sel_summary = policy.select_features(df_feat, val_report, engineer.registry)

    assert df_sel.height == df_feat.height
    assert "self_transfer_flag" in df_sel.columns  # Preserved domain critical feature
    assert len(sel_reg) > 0


def test_validator_decision_matrix(dummy_transactions):
    engineer = FeatureEngineer()
    df_feat = engineer.build_feature_store(dummy_transactions)

    validator = FeatureValidator(high_corr_thresh=0.80)
    val_report = validator.validate(df_feat)

    high_corr = val_report["correlation_summary"]["highly_correlated_pairs"]
    if high_corr:
        first_pair = high_corr[0]
        assert "feature_a" in first_pair
        assert "feature_b" in first_pair
        assert "decision" in first_pair
        assert "reason" in first_pair
        assert first_pair["decision"] in ["Keep", "Review"]
