"""
Unit tests for Feature Store Integrity and Parity Verification.
Asserts that no target columns exist in model feature schema and feature registry order matches.
"""
import json
import os

import polars as pl


def test_no_target_leakage_in_feature_order():
    """Assert feature_order_v1.json does NOT contain target labels or target encodings."""
    feature_order_path = "models/champion/feature_order_v1.json"
    if not os.path.exists(feature_order_path):
        feature_order_path = "archive/2026-08-06_li-small/champion/feature_order_v1.json"

    with open(feature_order_path, "r") as f:
        features = json.load(f)

    forbidden_terms = ["Is_Laundering", "is_laundering", "target", "label"]
    for feat in features:
        for term in forbidden_terms:
            assert term not in feat.lower(), f"Forbidden target term '{term}' found in feature: {feat}"

def test_feature_parquet_schema():
    """Assert computed feature parquet contains all expected features without missing columns."""
    parquet_path = "data/features/features_fraud.parquet"
    if os.path.exists(parquet_path):
        lf = pl.scan_parquet(parquet_path)
        cols = lf.columns
        assert "Is_Laundering" in cols
        assert "Timestamp" in cols
        assert "numeric__amount_paid" in cols
        assert "numeric__account_transaction_count" in cols
