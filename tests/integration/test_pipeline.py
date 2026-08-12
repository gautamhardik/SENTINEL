"""
Integration Edge-Case & Scale Stress Test Suite for PredictionEngine.
"""
import time

import pandas as pd
import polars as pl
import pytest

from fraud_detection import EngineFactory, HistoryRepository
from fraud_detection.exceptions import FeatureValidationError
from fraud_detection.io import DataReader, DataWriter


@pytest.fixture(scope="module")
def engine(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("integ_engine")
    repo = HistoryRepository(duckdb_path=tmp_path / "integ.duckdb", parquet_path=tmp_path / "integ.parquet")
    return EngineFactory.create(history_repository=repo)


@pytest.fixture(scope="module")
def sample_raw_transaction():
    import pandas as pd
    return pd.DataFrame([{
        "transaction_id": "tx_integ_001",
        "Timestamp": "2026-08-11 12:00:00",
        "From_Account": "acct_integ_1",
        "To_Account": "acct_integ_2",
        "From_Bank": "10",
        "To_Bank": "20",
        "Amount_Paid": 500.0,
        "Amount_Received": 500.0,
        "Payment_Format": "ACH",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    }])


def test_integration_valid_transaction(engine, sample_raw_transaction):
    session = engine.predict(sample_raw_transaction)
    assert session.request_id.startswith("req_")
    assert session.decision in ["APPROVED_LEGITIMATE", "APPROVED_WITH_MONITORING", "FLAGGED_FRAUD", "FLAGGED_CRITICAL_FRAUD"]
    assert 0.0 <= session.calibrated_probability <= 1.0
    assert session.total_latency_ms > 0
    assert "validation" in session.stage_latencies_ms


def test_integration_detailed_error_messages(engine, sample_raw_transaction):
    invalid_df = sample_raw_transaction.drop(columns=["Amount_Paid"])
    with pytest.raises(FeatureValidationError) as exc_info:
        engine.predict(invalid_df)
    assert "Missing required feature column: 'Amount_Paid'" in str(exc_info.value)


def test_integration_batch_scale_testing(engine, sample_raw_transaction):
    """Tests batch prediction scalability across 10, 100, and 1,000 transactions."""
    for batch_size in [10, 100, 1000]:
        batch_df = pd.concat([sample_raw_transaction] * batch_size, ignore_index=True)
        t0 = time.time()
        sessions = engine.predict_batch(batch_df, include_explanations=(batch_size <= 100))
        t_duration = (time.time() - t0) * 1000.0

        assert len(sessions) == batch_size
        per_tx_latency = t_duration / batch_size
        print(f"Batch size {batch_size:4d}: Total Latency = {t_duration:6.2f} ms | Per-Tx Latency = {per_tx_latency:5.3f} ms")


def test_data_io_readers_writers(tmp_path):
    df_sample = pl.DataFrame({"a": [1, 2], "b": [3.0, 4.0]})
    parquet_path = tmp_path / "test.parquet"
    out_p = DataWriter.export_batch(df_sample, parquet_path)
    read_p = DataReader.read_file(out_p)
    assert read_p.height == 2

    csv_path = tmp_path / "test.csv"
    out_c = DataWriter.export_batch(df_sample, csv_path)
    read_c = DataReader.read_file(out_c)
    assert read_c.height == 2
