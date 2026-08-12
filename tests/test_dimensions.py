"""
Modular test suite for Dimension Loading & Surrogate Key Lookups.
"""
from datetime import datetime

import polars as pl

from src.warehouse.database import SQL_DIR, WarehouseConnection
from src.warehouse.etl_engine import WarehouseETLEngine
from src.warehouse.logger import SQLRunner


def test_dimension_loader():
    conn_mgr = WarehouseConnection(engine_type="duckdb")
    runner = SQLRunner(conn_mgr)
    runner.execute_file(SQL_DIR / "01_schema.sql")

    sample_df = pl.DataFrame([
        {
            "Timestamp": datetime.now(),
            "From_Bank": 101,
            "From_Account": "ACC_111",
            "To_Bank": 202,
            "To_Account": "ACC_222",
            "Payment_Currency": "USD",
            "Receiving_Currency": "USD",
            "Payment_Format": "Wire"
        }
    ])

    engine = WarehouseETLEngine(conn_mgr)
    stats, duration = engine.load_dimensions(sample_df)
    assert stats["dim_bank"] >= 1
    assert stats["dim_account"] >= 1
    assert duration >= 0.0
    conn_mgr.close()
