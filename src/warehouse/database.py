"""
Centralized Warehouse Configuration & Database Engine Manager.
"""
import logging
import os
from pathlib import Path
from typing import Any, Optional

import duckdb

logger = logging.getLogger("WarehouseConnection")

# Environment Settings
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = PROJECT_ROOT / "sql"
CLEAN_DATA_PATH = PROJECT_ROOT / "data" / "cleaned" / "transactions_clean.parquet"
DUCKDB_PATH = PROJECT_ROOT / "data" / "warehouse.duckdb"
DOCS_DIR = PROJECT_ROOT / "docs"
LOGS_DIR = PROJECT_ROOT / "logs"

DB_ENGINE_TYPE = os.getenv("DB_ENGINE_TYPE", "postgresql")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "fraud_detection")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
BATCH_SIZE = 1000

SCHEMA_VERSION = 1

CREATE_ONLINE_STORE_DDL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INT PRIMARY KEY,
    description VARCHAR(255) NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS account_states (
    account_id VARCHAR(100) PRIMARY KEY,
    transaction_count BIGINT NOT NULL DEFAULT 0,
    total_amount_paid DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    total_amount_received DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    amount_sum_sq DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    last_transaction_timestamp TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transaction_history (
    transaction_key VARCHAR(100) PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    from_account VARCHAR(100) NOT NULL,
    to_account VARCHAR(100) NOT NULL,
    from_bank VARCHAR(100) NOT NULL,
    to_bank VARCHAR(100) NOT NULL,
    amount_paid DOUBLE PRECISION NOT NULL,
    amount_received DOUBLE PRECISION NOT NULL,
    payment_format VARCHAR(50) NOT NULL,
    payment_currency VARCHAR(10) NOT NULL,
    receiving_currency VARCHAR(10) NOT NULL,
    is_laundering INT DEFAULT 0 NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tx_from_acct_ts ON transaction_history (from_account, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_tx_to_acct_ts ON transaction_history (to_account, timestamp DESC);
"""

class WarehouseConnection:
    """Encapsulates connection pooling and session connectivity for PostgreSQL and DuckDB."""
    _shared_duckdb_conn: Any = None

    def __init__(self, engine_type: Optional[str] = None, db_path: Optional[Path] = None, read_only: bool = False):
        self.engine_type = (engine_type or DB_ENGINE_TYPE).lower()
        self.db_path = Path(db_path) if db_path else DUCKDB_PATH
        self.read_only = read_only
        self.conn = None

    def connect(self, read_only: Optional[bool] = None) -> Any:
        if self.conn is not None:
            try:
                if self.engine_type == "postgresql":
                    with self.conn.cursor() as cur:
                        cur.execute("SELECT 1;")
                else:
                    self.conn.execute("SELECT 1;")
                return self.conn
            except Exception:
                self.conn = None

        if self.engine_type == "postgresql":
            import psycopg2
            try:
                db_url = os.getenv("DATABASE_URL", None)
                if db_url and ("neon.tech" in db_url or "sslmode=" in db_url or "postgres://" in db_url or "postgresql://" in db_url):
                    self.conn = psycopg2.connect(db_url, connect_timeout=10)
                else:
                    self.conn = psycopg2.connect(
                        host=os.getenv("POSTGRES_HOST", POSTGRES_HOST),
                        port=int(os.getenv("POSTGRES_PORT", str(POSTGRES_PORT))),
                        dbname=os.getenv("POSTGRES_DB", POSTGRES_DB),
                        user=os.getenv("POSTGRES_USER", POSTGRES_USER),
                        password=os.getenv("POSTGRES_PASSWORD", POSTGRES_PASSWORD),
                        sslmode=os.getenv("POSTGRES_SSLMODE", os.getenv("SSLMODE", "prefer")),
                        connect_timeout=10
                    )
                return self.conn
            except Exception as e:
                # If running locally outside Docker (POSTGRES_HOST == localhost), fall back to DuckDB for seamless local dev
                current_host = os.getenv("POSTGRES_HOST", POSTGRES_HOST)
                fallback_env = os.getenv("DB_FALLBACK_TO_DUCKDB", "true").lower() in ("true", "1", "yes")
                is_local = current_host in ("localhost", "127.0.0.1")
                if fallback_env and is_local:
                    import logging
                    logging.getLogger("WarehouseConnection").warning(
                        f"PostgreSQL connection at {current_host} failed ({e}). "
                        f"Falling back to local DuckDB warehouse storage for seamless local operation."
                    )
                    self.engine_type = "duckdb"
                    return self.connect(read_only=read_only)
                raise e

        else:
            if str(self.db_path) == str(DUCKDB_PATH) and WarehouseConnection._shared_duckdb_conn is not None:
                try:
                    WarehouseConnection._shared_duckdb_conn.execute("SELECT 1;")
                    self.conn = WarehouseConnection._shared_duckdb_conn
                    return self.conn
                except Exception:
                    WarehouseConnection._shared_duckdb_conn = None

            try:
                self.conn = duckdb.connect(str(self.db_path))
            except Exception as e:
                logger.warning(f"DuckDB disk connection failed for {self.db_path}: {e}. Falling back to in-memory mode.")
                self.conn = duckdb.connect(":memory:")

            if str(self.db_path) == str(DUCKDB_PATH):
                WarehouseConnection._shared_duckdb_conn = self.conn
            return self.conn

    def init_schema(self) -> None:
        """Deterministically initializes schema version, account_states, and transaction_history tables."""
        conn = self.connect()
        if self.engine_type == "postgresql":
            with conn.cursor() as cur:
                cur.execute("CREATE TABLE IF NOT EXISTS schema_version (version INT PRIMARY KEY, description VARCHAR(255) NOT NULL, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
                cur.execute("CREATE TABLE IF NOT EXISTS account_states (account_id VARCHAR(100) PRIMARY KEY, transaction_count BIGINT NOT NULL DEFAULT 0, total_amount_paid DOUBLE PRECISION NOT NULL DEFAULT 0.0, total_amount_received DOUBLE PRECISION NOT NULL DEFAULT 0.0, amount_sum_sq DOUBLE PRECISION NOT NULL DEFAULT 0.0, last_transaction_timestamp TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
                cur.execute("CREATE TABLE IF NOT EXISTS transaction_history (transaction_key VARCHAR(100) PRIMARY KEY, timestamp TIMESTAMP NOT NULL, from_account VARCHAR(100) NOT NULL, to_account VARCHAR(100) NOT NULL, from_bank VARCHAR(100) NOT NULL, to_bank VARCHAR(100) NOT NULL, amount_paid DOUBLE PRECISION NOT NULL, amount_received DOUBLE PRECISION NOT NULL, payment_format VARCHAR(50) NOT NULL, payment_currency VARCHAR(10) NOT NULL, receiving_currency VARCHAR(10) NOT NULL, is_laundering INT DEFAULT 0 NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_from_acct_ts ON transaction_history (from_account, timestamp DESC);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_to_acct_ts ON transaction_history (to_account, timestamp DESC);")
                cur.execute("INSERT INTO schema_version (version, description) VALUES (%s, %s) ON CONFLICT (version) DO NOTHING;", (SCHEMA_VERSION, 'Online Feature Store Hardening Schema v1'))
            conn.commit()
        else:
            conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INT PRIMARY KEY, description VARCHAR(255) NOT NULL, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
            conn.execute("CREATE TABLE IF NOT EXISTS account_states (account_id VARCHAR(100) PRIMARY KEY, transaction_count BIGINT NOT NULL DEFAULT 0, total_amount_paid DOUBLE PRECISION NOT NULL DEFAULT 0.0, total_amount_received DOUBLE PRECISION NOT NULL DEFAULT 0.0, amount_sum_sq DOUBLE PRECISION NOT NULL DEFAULT 0.0, last_transaction_timestamp TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
            conn.execute("CREATE TABLE IF NOT EXISTS transaction_history (transaction_key VARCHAR(100) PRIMARY KEY, timestamp TIMESTAMP NOT NULL, from_account VARCHAR(100) NOT NULL, to_account VARCHAR(100) NOT NULL, from_bank VARCHAR(100) NOT NULL, to_bank VARCHAR(100) NOT NULL, amount_paid DOUBLE PRECISION NOT NULL, amount_received DOUBLE PRECISION NOT NULL, payment_format VARCHAR(50) NOT NULL, payment_currency VARCHAR(10) NOT NULL, receiving_currency VARCHAR(10) NOT NULL, is_laundering INT DEFAULT 0 NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_from_acct_ts ON transaction_history (from_account, timestamp DESC);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_to_acct_ts ON transaction_history (to_account, timestamp DESC);")
            conn.execute("INSERT INTO schema_version (version, description) VALUES (?, ?) ON CONFLICT (version) DO NOTHING;", (SCHEMA_VERSION, 'Online Feature Store Hardening Schema v1'))

    def test_connection(self) -> bool:
        try:
            conn = self.connect()
            if self.engine_type == "postgresql":
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
            else:
                conn.execute("SELECT 1;")
            return True
        except Exception as e:
            import logging
            logging.getLogger("WarehouseConnection").warning(f"Connection test failed: {e}")
            return False

    def close(self) -> None:
        if WarehouseConnection._shared_duckdb_conn is not None:
            try:
                WarehouseConnection._shared_duckdb_conn.close()
            except Exception:
                pass
            WarehouseConnection._shared_duckdb_conn = None
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None
            WarehouseConnection._shared_duckdb_conn = None
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

