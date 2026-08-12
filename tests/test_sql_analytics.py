"""
Modular test suite for Phase 3 SQL Analytics & Reporting Views.
"""
from src.analytics.executor import AnalyticsExecutor
from src.analytics.reporter import AnalyticsReporter
from src.warehouse.database import SQL_DIR, WarehouseConnection
from src.warehouse.logger import SQLRunner


def test_analytics_executor():
    conn_mgr = WarehouseConnection(engine_type="duckdb")
    runner = SQLRunner(conn_mgr)
    runner.execute_file(SQL_DIR / "01_schema.sql")

    executor = AnalyticsExecutor(conn_mgr)
    results = executor.execute_script(SQL_DIR / "04_business_analytics.sql")
    assert len(results) > 0
    assert results[0]["dataframe"] is not None
    conn_mgr.close()

def test_reporting_views():
    conn_mgr = WarehouseConnection(engine_type="duckdb")
    runner = SQLRunner(conn_mgr)
    runner.execute_file(SQL_DIR / "01_schema.sql")
    runner.execute_file(SQL_DIR / "05_reporting_views.sql")

    executor = AnalyticsExecutor(conn_mgr)
    df = executor.query("SELECT * FROM vw_daily_fraud_summary;")
    assert df is not None
    conn_mgr.close()

def test_analytics_reporter():
    reporter = AnalyticsReporter()
    assert reporter.output_dir.exists()
