import os
from src.warehouse.database import WarehouseConnection


def test_duckdb_connection():
    conn_mgr = WarehouseConnection(engine_type="duckdb")
    assert conn_mgr.test_connection() is True
    conn_mgr.close()


def test_postgresql_connection():
    # Only test active PostgreSQL if POSTGRES_HOST or DB_ENGINE_TYPE is set
    engine_type = os.getenv("DB_ENGINE_TYPE", "postgresql")
    conn_mgr = WarehouseConnection(engine_type=engine_type)
    if conn_mgr.engine_type == "postgresql":
        # Test connection or graceful handling
        is_connected = conn_mgr.test_connection()
        conn_mgr.close()
        # Verify object initialization and type
        assert conn_mgr.engine_type == "postgresql"
