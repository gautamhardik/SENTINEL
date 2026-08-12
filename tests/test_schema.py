"""
Modular test suite for DDL Schema Execution & Analytical Views.
"""
from src.warehouse.database import SQL_DIR, WarehouseConnection
from src.warehouse.logger import SQLRunner


def test_schema_execution():
    conn_mgr = WarehouseConnection(engine_type="duckdb")
    runner = SQLRunner(conn_mgr)
    runner.execute_file(SQL_DIR / "01_schema.sql")
    runner.execute_file(SQL_DIR / "02_views.sql")

    tables = conn_mgr.connect().execute("SHOW TABLES").fetchall()
    table_names = [t[0] for t in tables]
    assert "fact_transactions" in table_names
    assert "dim_bank" in table_names
    assert "dim_account" in table_names
    conn_mgr.close()
