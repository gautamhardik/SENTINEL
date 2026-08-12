"""
Test vectorized batch inference and account deduplication querying.
"""
from fraud_detection.factories import EngineFactory
from fraud_detection.history import HistoryRepository


def test_batch_inference_raw_transactions(tmp_path):
    """Verifies batch raw transaction inference."""
    repo = HistoryRepository(duckdb_path=tmp_path / "batch.duckdb", parquet_path=tmp_path / "batch.parquet")
    engine = EngineFactory.create(history_repository=repo)

    batch_payload = [
        {
            "transaction_id": f"batch_tx_{i}",
            "Timestamp": f"2026-08-06 16:0{i % 10}:00",
            "From_Account": f"batch_user_{i % 5}",  # Deduplicated unique accounts
            "To_Account": f"batch_merchant_{i % 3}",
            "From_Bank": "10",
            "To_Bank": "20",
            "Amount_Paid": 100.0 * (i + 1),
            "Amount_Received": 100.0 * (i + 1),
            "Payment_Format": "ACH",
            "Payment_Currency": "USD",
            "Receiving_Currency": "USD"
        }
        for i in range(20)
    ]

    sessions = engine.predict_batch(batch_payload, include_explanations=False)

    assert len(sessions) == 20
    for s in sessions:
        assert s.decision in ["APPROVED_LEGITIMATE", "APPROVED_WITH_MONITORING", "FLAGGED_FRAUD", "FLAGGED_CRITICAL_FRAUD"]
        assert 0.0 <= s.calibrated_probability <= 1.0
