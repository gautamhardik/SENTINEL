"""
Modular test suite for 25+ Integrity Checks & Quality Scorecard.
"""
from src.warehouse.database import SQL_DIR, WarehouseConnection
from src.warehouse.logger import SQLRunner
from src.warehouse.validator import WarehouseValidator


def test_validator_suite():
    conn_mgr = WarehouseConnection(engine_type="duckdb")
    runner = SQLRunner(conn_mgr)
    runner.execute_file(SQL_DIR / "01_schema.sql")

    validator = WarehouseValidator(conn_mgr)
    val_results, duration = validator.validate_warehouse()
    assert "fact_transaction_count" in val_results
    assert "completeness_score_pct" in val_results
    assert duration >= 0.0
    conn_mgr.close()
