"""
Test PredictionEngine dual-input overload capability (raw transactions vs pre-engineered vectors).
"""
import pandas as pd

from fraud_detection.factories import EngineFactory
from fraud_detection.history import HistoryRepository
from fraud_detection.registry import ArtifactLoader


def test_prediction_engine_raw_dict(tmp_path):
    """Verifies predict() with a raw transaction dictionary."""
    repo = HistoryRepository(duckdb_path=tmp_path / "raw.duckdb", parquet_path=tmp_path / "raw.parquet")
    engine = EngineFactory.create(history_repository=repo)
    raw_tx = {
        "transaction_id": "overload_raw_001",
        "Timestamp": "2026-08-06 15:00:00",
        "From_Account": "user_11",
        "To_Account": "merchant_22",
        "From_Bank": "10",
        "To_Bank": "20",
        "Amount_Paid": 450.0,
        "Amount_Received": 450.0,
        "Payment_Format": "ACH",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    }

    session = engine.predict(raw_tx)
    assert session is not None
    assert session.request_id is not None
    assert 0.0 <= session.calibrated_probability <= 1.0


def test_prediction_engine_pre_engineered_dataframe(tmp_path):
    """Verifies predict() with a pre-engineered feature vector DataFrame."""
    repo = HistoryRepository(duckdb_path=tmp_path / "pre.duckdb", parquet_path=tmp_path / "pre.parquet")
    engine = EngineFactory.create(history_repository=repo)
    loader = ArtifactLoader()
    assets = loader.load_assets()
    feature_order = assets["feature_order"]

    # Create dummy 1-row pre-engineered DataFrame
    data = {col: [1.0] for col in feature_order}
    df_pre_engineered = pd.DataFrame(data)

    session = engine.predict(df_pre_engineered)
    assert session is not None
    assert session.request_id is not None
    assert 0.0 <= session.calibrated_probability <= 1.0
