"""
Test cold start zero-history account behavior.
"""
from fraud_detection.core import RawTransaction
from fraud_detection.factories import EngineFactory
from fraud_detection.feature_service import OnlineFeatureService
from fraud_detection.history import HistoryRepository
from fraud_detection.retrieval import ContextService


def test_cold_start_feature_generation(tmp_path):
    """Verifies that a brand-new account with zero history generates clean non-null features."""
    repo = HistoryRepository(duckdb_path=tmp_path / "cold.duckdb", parquet_path=tmp_path / "cold.parquet")
    # Force empty in-memory repository
    repo.clear()

    ctx_service = ContextService(repository=repo, reference_priors={
        "global_priors": {"fraud_rate": 0.015},
        "bank_fraud_rate": {"10": 0.012},
        "payment_format_risk": {"ACH": 0.008},
        "currency_risk": {"USD": 0.011}
    })

    feature_order = [
        "numeric__Amount_Paid", "numeric__Amount_Received", "numeric__account_avg_amount",
        "numeric__seconds_since_last_tx", "numeric__bank_fraud_rate", "numeric__rolling_mean_5"
    ]
    service = OnlineFeatureService(context_service=ctx_service, feature_order=feature_order)

    raw_tx = RawTransaction.from_dict({
        "transaction_id": "tx_cold_001",
        "Timestamp": "2026-08-06 12:00:00",
        "From_Account": "new_account_999",
        "To_Account": "new_receiver_888",
        "From_Bank": "10",
        "To_Bank": "20",
        "Amount_Paid": 500.0,
        "Amount_Received": 500.0,
        "Payment_Format": "ACH",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    })

    df_feats = service.build_features_single(raw_tx)

    assert not df_feats.empty
    assert len(df_feats) == 1
    assert df_feats["numeric__Amount_Paid"].iloc[0] == 500.0
    assert df_feats["numeric__account_avg_amount"].iloc[0] == 500.0  # Cold start fallback to current amount
    assert df_feats["numeric__seconds_since_last_tx"].iloc[0] == 999999.0  # Cold start fallback
    assert df_feats["numeric__bank_fraud_rate"].iloc[0] == 0.012
    assert df_feats["numeric__rolling_mean_5"].iloc[0] == 500.0
    assert df_feats.isna().sum().sum() == 0


def test_cold_start_engine_prediction(tmp_path):
    """Verifies that PredictionEngine successfully runs inference on cold start transactions."""
    repo = HistoryRepository(duckdb_path=tmp_path / "cold_eng.duckdb", parquet_path=tmp_path / "cold_eng.parquet")
    engine = EngineFactory.create(history_repository=repo)
    raw_tx = {
        "transaction_id": "tx_cold_002",
        "Timestamp": "2026-08-06 12:05:00",
        "From_Account": "brand_new_cust_123",
        "To_Account": "brand_new_merchant_456",
        "From_Bank": "10",
        "To_Bank": "20",
        "Amount_Paid": 1250.0,
        "Amount_Received": 1250.0,
        "Payment_Format": "ACH",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    }

    session = engine.predict(raw_tx)
    assert session is not None

    assert session.decision in ["APPROVED_LEGITIMATE", "APPROVED_WITH_MONITORING", "FLAGGED_FRAUD", "FLAGGED_CRITICAL_FRAUD"]
    assert 0.0 <= session.calibrated_probability <= 1.0
