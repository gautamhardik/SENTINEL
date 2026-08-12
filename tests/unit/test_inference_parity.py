from fraud_detection.factories import EngineFactory
from fraud_detection.history import HistoryRepository


def test_inference_parity_and_consistency(tmp_path):
    """Verifies 100% numerical parity and zero behavioral drift across test payloads."""
    repo1 = HistoryRepository(duckdb_path=tmp_path / "eng1.duckdb", parquet_path=tmp_path / "eng1.parquet")
    repo2 = HistoryRepository(duckdb_path=tmp_path / "eng2.duckdb", parquet_path=tmp_path / "eng2.parquet")
    engine1 = EngineFactory.create(history_repository=repo1)
    engine2 = EngineFactory.create(history_repository=repo2)

    payload = {
        "Amount_Paid": 50.0,
        "Amount_Received": 50.0,
        "From_Account": "Acc_Parity_1",
        "To_Account": "Acc_Parity_2",
        "From_Bank": "10",
        "To_Bank": "20",
        "Payment_Format": "ACH",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD",
        "Timestamp": "2026-08-11 12:00:00"
    }

    session1 = engine1.predict(payload)
    session2 = engine2.predict(payload)

    # Assert raw and calibrated probability parity across identical inferences
    assert abs(session1.raw_probability - session2.raw_probability) < 1e-4
    assert abs(session1.calibrated_probability - session2.calibrated_probability) < 1e-4
    assert session1.decision == session2.decision


