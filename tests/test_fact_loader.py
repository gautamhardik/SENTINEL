"""
Modular test suite for Vectorized Fact Loading.
"""
from datetime import datetime

import polars as pl

from src.warehouse.database import SQL_DIR, WarehouseConnection
from src.warehouse.etl_engine import WarehouseETLEngine
from src.warehouse.logger import SQLRunner


def test_fact_loader():
    conn_mgr = WarehouseConnection(engine_type="duckdb")
    runner = SQLRunner(conn_mgr)
    runner.execute_file(SQL_DIR / "01_schema.sql")

    sample_df = pl.DataFrame([
        {
            "TransactionID": "TX_TEST_99",
            "Timestamp": datetime.now(),
            "From_Bank": 101,
            "From_Account": "ACC_111",
            "To_Bank": 202,
            "To_Account": "ACC_222",
            "Payment_Currency": "USD",
            "Receiving_Currency": "USD",
            "Payment_Format": "Wire",
            "Amount_Paid": 5000.0,
            "Amount_Received": 5000.0,
            "Is_Laundering": 0
        }
    ])

    engine = WarehouseETLEngine(conn_mgr)
    engine.load_dimensions(sample_df)
    fact_stats, duration = engine.load_fact(sample_df)
    assert fact_stats["total_inserted"] == 1
    assert duration >= 0.0
    conn_mgr.close()
