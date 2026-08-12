"""
Test history persistence ensuring sequential transactions update real-time context.
"""
from fraud_detection.core import RawTransaction
from fraud_detection.feature_service import OnlineFeatureService
from fraud_detection.history import HistoryRepository, HistoryWriter
from fraud_detection.retrieval import ContextService


def test_history_persistence_flow(tmp_path):
    """Verifies that TX1 is persisted so TX2 sees updated transaction count and velocity."""
    repo = HistoryRepository(duckdb_path=tmp_path / "hist.duckdb", parquet_path=tmp_path / "hist.parquet")
    # Start clean
    repo.clear()
    writer = HistoryWriter(repository=repo)

    ctx_service = ContextService(repository=repo)
    feature_order = [
        "numeric__Amount_Paid", "numeric__account_transaction_count", "numeric__seconds_since_last_tx"
    ]
    feat_service = OnlineFeatureService(context_service=ctx_service, feature_order=feature_order)

    tx1 = RawTransaction.from_dict({
        "transaction_id": "seq_tx_1",
        "Timestamp": "2026-08-06 10:00:00",
        "From_Account": "seq_user_001",
        "To_Account": "seq_merchant_001",
        "From_Bank": "10",
        "To_Bank": "20",
        "Amount_Paid": 100.0,
        "Amount_Received": 100.0,
        "Payment_Format": "ACH",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    })

    # Features for TX1 (before TX1 is in DB)
    f1 = feat_service.build_features_single(tx1)
    assert f1["numeric__account_transaction_count"].iloc[0] == 0.0
    assert f1["numeric__seconds_since_last_tx"].iloc[0] == 999999.0

    # Persist TX1
    writer.persist_transaction(tx1)

    # Features for TX2 (at 10:02:00 -> 120 seconds later)
    tx2 = RawTransaction.from_dict({
        "transaction_id": "seq_tx_2",
        "Timestamp": "2026-08-06 10:02:00",
        "From_Account": "seq_user_001",
        "To_Account": "seq_merchant_002",
        "From_Bank": "10",
        "To_Bank": "20",
        "Amount_Paid": 200.0,
        "Amount_Received": 200.0,
        "Payment_Format": "ACH",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    })

    f2 = feat_service.build_features_single(tx2)
    assert f2["numeric__account_transaction_count"].iloc[0] == 1.0
    assert abs(f2["numeric__seconds_since_last_tx"].iloc[0] - 120.0) < 1e-3
