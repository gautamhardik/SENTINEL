from pathlib import Path
from typing import List, Optional, Union, cast
import logging
import threading

import duckdb
import pandas as pd

try:
    from src.warehouse.database import WarehouseConnection
except ImportError:
    try:
        from warehouse.database import WarehouseConnection
    except ImportError:
        from fraud_detection.warehouse.database import WarehouseConnection

logger = logging.getLogger("HistoryRepository")

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CLEAN_PARQUET_PATH = PROJECT_ROOT / "data" / "cleaned" / "transactions_clean.parquet"
DUCKDB_PATH = PROJECT_ROOT / "data" / "warehouse.duckdb"


class HistoryRepository:
    """Provides persistent, thread-safe, and process-safe historical account and transaction queries."""

    def __init__(
        self,
        parquet_path: Optional[Union[Path, str]] = None,
        duckdb_path: Optional[Union[Path, str]] = None,
        engine_type: Optional[str] = None,
        bootstrap_data: bool = False
    ):
        self.parquet_path = Path(parquet_path) if parquet_path else CLEAN_PARQUET_PATH
        self.duckdb_path = Path(duckdb_path) if duckdb_path else DUCKDB_PATH
        self.db = WarehouseConnection(engine_type=engine_type, db_path=self.duckdb_path)
        self._lock = threading.Lock()
        self._in_memory_df: Optional[pd.DataFrame] = None
        self.bootstrap_data = bootstrap_data
        self._init_db_and_data()
        self._seed_benchmark_profiles_if_needed()

    def _seed_benchmark_profiles_if_needed(self) -> None:
        """Seeds benchmark account histories into DB if they do not already exist."""
        benchmark_txs = pd.DataFrame([
            # ACC_ROUTINE_101 low-risk clean history
            {
                "transaction_key": "TX_SEED_ROUTINE_01",
                "Timestamp": "2026-08-13 10:00:00",
                "From_Account": "ACC_ROUTINE_101",
                "To_Account": "ACC_ROUTINE_102",
                "From_Bank": "10",
                "To_Bank": "10",
                "Amount_Paid": 45.50,
                "Amount_Received": 45.50,
                "Payment_Format": "ACH Outbound",
                "Payment_Currency": "USD",
                "Receiving_Currency": "USD",
                "is_laundering": 0
            },
            # ACC_HIGH_VAL_601 high risk seed chain
            {
                "transaction_key": "TX_SEED_HIGH_01",
                "Timestamp": "2026-08-13 12:30:00",
                "From_Account": "ACC_HIGH_VAL_601",
                "To_Account": "ACC_HIGH_VAL_602",
                "From_Bank": "10",
                "To_Bank": "99",
                "Amount_Paid": 75000.00,
                "Amount_Received": 75000.00,
                "Payment_Format": "Wire Transfer",
                "Payment_Currency": "USD",
                "Receiving_Currency": "USD",
                "is_laundering": 1
            },
            {
                "transaction_key": "TX_SEED_HIGH_02",
                "Timestamp": "2026-08-13 12:40:00",
                "From_Account": "ACC_HIGH_VAL_601",
                "To_Account": "ACC_HIGH_VAL_602",
                "From_Bank": "10",
                "To_Bank": "99",
                "Amount_Paid": 75000.00,
                "Amount_Received": 75000.00,
                "Payment_Format": "Wire Transfer",
                "Payment_Currency": "USD",
                "Receiving_Currency": "USD",
                "is_laundering": 1
            }
        ])
        try:
            self.add_transactions(benchmark_txs)
        except Exception as e:
            logger.debug(f"Benchmark profile seeding warning: {e}")

    def _init_db_and_data(self) -> None:
        """Initializes persistent DB schema and optionally loads initial data bootstrap."""
        try:
            self.db.init_schema()
        except Exception as e:
            logger.warning(f"DB schema init warning (falling back to memory mode): {e}")

        if self.bootstrap_data:
            self._load_initial_data()
        else:
            self._in_memory_df = pd.DataFrame(columns=[
                "transaction_key", "Timestamp", "From_Account", "To_Account", "From_Bank", "To_Bank",
                "Amount_Paid", "Amount_Received", "Payment_Format", "Payment_Currency", "Receiving_Currency", "is_laundering"
            ])

    def close(self) -> None:
        """Closes underlying database connection and releases resources."""
        if hasattr(self, "db") and self.db is not None:
            try:
                self.db.close()
            except Exception:
                pass

    def _load_initial_data(self) -> None:
        """Explicit admin/offline fallback loading historical transactions into memory. Must be explicitly requested via bootstrap_data=True."""
        if self.parquet_path.exists():
            try:
                self._in_memory_df = pd.read_parquet(self.parquet_path)
                return
            except Exception:
                pass

        if self.duckdb_path.exists():
            try:
                conn = duckdb.connect(str(self.duckdb_path), read_only=True)
                tables = [t[0] for t in conn.execute("SHOW TABLES;").fetchall()]
                target_table = "fact_transactions" if "fact_transactions" in tables else (tables[0] if tables else None)
                if target_table:
                    self._in_memory_df = cast(pd.DataFrame, conn.execute(f"SELECT * FROM {target_table}").df())
                conn.close()
                return
            except Exception:
                pass

        self._in_memory_df = pd.DataFrame(columns=[
            "transaction_key", "Timestamp", "From_Account", "To_Account", "From_Bank", "To_Bank",
            "Amount_Paid", "Amount_Received", "Payment_Format", "Payment_Currency", "Receiving_Currency", "is_laundering"
        ])

    def get_account_history(self, account_ids: List[str]) -> pd.DataFrame:
        """Fetches prior transactions where From_Account is in account_ids."""
        if not account_ids:
            return pd.DataFrame()

        acct_list = [a for a in account_ids if a is not None]
        if not acct_list:
            return pd.DataFrame()

        db_df = pd.DataFrame()
        try:
            conn = self.db.connect()
            if self.db.engine_type == "postgresql":
                placeholders = ",".join(["%s"] * len(acct_list))
                query = f"""
                SELECT transaction_key, timestamp AS "Timestamp", from_account AS "From_Account", to_account AS "To_Account",
                       from_bank AS "From_Bank", to_bank AS "To_Bank", amount_paid AS "Amount_Paid", amount_received AS "Amount_Received",
                       payment_format AS "Payment_Format", payment_currency AS "Payment_Currency", receiving_currency AS "Receiving_Currency",
                       is_laundering
                FROM transaction_history
                WHERE from_account IN ({placeholders})
                ORDER BY timestamp ASC
                """
                db_df = pd.read_sql_query(query, conn, params=tuple(acct_list))
            else:
                placeholders = ",".join(["?"] * len(acct_list))
                query = f"""
                SELECT transaction_key, timestamp AS "Timestamp", from_account AS "From_Account", to_account AS "To_Account",
                       from_bank AS "From_Bank", to_bank AS "To_Bank", amount_paid AS "Amount_Paid", amount_received AS "Amount_Received",
                       payment_format AS "Payment_Format", payment_currency AS "Payment_Currency", receiving_currency AS "Receiving_Currency",
                       is_laundering
                FROM transaction_history
                WHERE from_account IN ({placeholders})
                ORDER BY timestamp ASC
                """
                db_df = conn.execute(query, acct_list).df()
        except Exception as e:
            if self.db.engine_type == "postgresql":
                logger.error(f"PostgreSQL query get_account_history failed: {e}")
                raise RuntimeError(f"PostgreSQL database query failure: {e}") from e
            logger.debug(f"DB query get_account_history exception: {e}")

        mem_df = pd.DataFrame()
        if self._in_memory_df is not None and not self._in_memory_df.empty:
            acct_set = set(acct_list)
            mem_df = self._in_memory_df[self._in_memory_df["From_Account"].astype(str).isin(acct_set)].copy()

        if db_df.empty and mem_df.empty:
            return pd.DataFrame()

        combined = pd.concat([mem_df, db_df], ignore_index=True)
        if "transaction_key" in combined.columns:
            combined = combined.drop_duplicates(subset=["transaction_key"], keep="last")
        return combined

    def get_receiver_history(self, receiver_ids: List[str]) -> pd.DataFrame:
        """Fetches prior transactions where To_Account is in receiver_ids."""
        if not receiver_ids:
            return pd.DataFrame()

        rcvr_list = [r for r in receiver_ids if r is not None]
        if not rcvr_list:
            return pd.DataFrame()

        db_df = pd.DataFrame()
        try:
            conn = self.db.connect()
            if self.db.engine_type == "postgresql":
                placeholders = ",".join(["%s"] * len(rcvr_list))
                query = f"""
                SELECT transaction_key, timestamp AS "Timestamp", from_account AS "From_Account", to_account AS "To_Account",
                       from_bank AS "From_Bank", to_bank AS "To_Bank", amount_paid AS "Amount_Paid", amount_received AS "Amount_Received",
                       payment_format AS "Payment_Format", payment_currency AS "Payment_Currency", receiving_currency AS "Receiving_Currency",
                       is_laundering
                FROM transaction_history
                WHERE to_account IN ({placeholders})
                ORDER BY timestamp ASC
                """
                db_df = pd.read_sql_query(query, conn, params=tuple(rcvr_list))
            else:
                placeholders = ",".join(["?"] * len(rcvr_list))
                query = f"""
                SELECT transaction_key, timestamp AS "Timestamp", from_account AS "From_Account", to_account AS "To_Account",
                       from_bank AS "From_Bank", to_bank AS "To_Bank", amount_paid AS "Amount_Paid", amount_received AS "Amount_Received",
                       payment_format AS "Payment_Format", payment_currency AS "Payment_Currency", receiving_currency AS "Receiving_Currency",
                       is_laundering
                FROM transaction_history
                WHERE to_account IN ({placeholders})
                ORDER BY timestamp ASC
                """
                db_df = conn.execute(query, rcvr_list).df()
        except Exception as e:
            if self.db.engine_type == "postgresql":
                logger.error(f"PostgreSQL query get_receiver_history failed: {e}")
                raise RuntimeError(f"PostgreSQL database query failure: {e}") from e
            logger.debug(f"DB query get_receiver_history exception: {e}")

        mem_df = pd.DataFrame()
        if self._in_memory_df is not None and not self._in_memory_df.empty:
            rcvr_set = set(rcvr_list)
            mem_df = self._in_memory_df[self._in_memory_df["To_Account"].astype(str).isin(rcvr_set)].copy()

        if db_df.empty and mem_df.empty:
            return pd.DataFrame()

        combined = pd.concat([mem_df, db_df], ignore_index=True)
        if "transaction_key" in combined.columns:
            combined = combined.drop_duplicates(subset=["transaction_key"], keep="last")
        return combined

    def add_transactions(self, df_new: pd.DataFrame) -> None:
        """Appends new transactions atomically into persistent DB and memory state."""
        if df_new is None or df_new.empty:
            return

        with self._lock:
            local_df = df_new.copy()

            # Ensure expected column names
            col_map = {
                "transaction_id": "transaction_key",
                "is_amount_outlier": "is_laundering"
            }
            local_df = local_df.rename(columns={k: v for k, v in col_map.items() if k in local_df.columns})

            for _, row in local_df.iterrows():
                tx_key = str(row.get("transaction_key", "tx_000"))
                ts_str = str(row.get("Timestamp", "2026-08-06 12:00:00"))
                from_acct = str(row.get("From_Account", "acct_0"))
                to_acct = str(row.get("To_Account", "acct_1"))
                from_bank = str(row.get("From_Bank", "10"))
                to_bank = str(row.get("To_Bank", "20"))
                amt_paid = float(row.get("Amount_Paid", 0.0))
                amt_recv = float(row.get("Amount_Received", 0.0))
                fmt_str = str(row.get("Payment_Format", "ACH"))
                pay_curr = str(row.get("Payment_Currency", "USD"))
                recv_curr = str(row.get("Receiving_Currency", "USD"))
                is_laundering = int(row.get("is_laundering", 0))

                try:
                    conn = self.db.connect()
                    inserted = False

                    if self.db.engine_type == "postgresql":
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                INSERT INTO transaction_history (
                                    transaction_key, timestamp, from_account, to_account, from_bank, to_bank,
                                    amount_paid, amount_received, payment_format, payment_currency, receiving_currency, is_laundering
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (transaction_key) DO NOTHING;
                                """,
                                (tx_key, ts_str, from_acct, to_acct, from_bank, to_bank, amt_paid, amt_recv, fmt_str, pay_curr, recv_curr, is_laundering)
                            )
                            if cur.rowcount > 0:
                                inserted = True
                                # Atomic account state update (Sender)
                                cur.execute(
                                    """
                                    INSERT INTO account_states (account_id, transaction_count, total_amount_paid, total_amount_received, amount_sum_sq, last_transaction_timestamp, updated_at)
                                    VALUES (%s, 1, %s, 0.0, %s, %s, CURRENT_TIMESTAMP)
                                    ON CONFLICT (account_id) DO UPDATE SET
                                        transaction_count = account_states.transaction_count + 1,
                                        total_amount_paid = account_states.total_amount_paid + EXCLUDED.total_amount_paid,
                                        amount_sum_sq = account_states.amount_sum_sq + EXCLUDED.amount_sum_sq,
                                        last_transaction_timestamp = EXCLUDED.last_transaction_timestamp,
                                        updated_at = CURRENT_TIMESTAMP;
                                    """,
                                    (from_acct, amt_paid, amt_paid * amt_paid, ts_str)
                                )
                                # Atomic account state update (Receiver)
                                cur.execute(
                                    """
                                    INSERT INTO account_states (account_id, transaction_count, total_amount_paid, total_amount_received, amount_sum_sq, last_transaction_timestamp, updated_at)
                                    VALUES (%s, 0, 0.0, %s, 0.0, %s, CURRENT_TIMESTAMP)
                                    ON CONFLICT (account_id) DO UPDATE SET
                                        total_amount_received = account_states.total_amount_received + EXCLUDED.total_amount_received,
                                        updated_at = CURRENT_TIMESTAMP;
                                    """,
                                    (to_acct, amt_recv, ts_str)
                                )
                        conn.commit()
                    else:
                        # DuckDB transaction
                        existing = conn.execute("SELECT 1 FROM transaction_history WHERE transaction_key = ?", [tx_key]).fetchone()
                        if not existing:
                            inserted = True
                            conn.execute(
                                """
                                INSERT INTO transaction_history (
                                    transaction_key, timestamp, from_account, to_account, from_bank, to_bank,
                                    amount_paid, amount_received, payment_format, payment_currency, receiving_currency, is_laundering
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                                """,
                                (tx_key, ts_str, from_acct, to_acct, from_bank, to_bank, amt_paid, amt_recv, fmt_str, pay_curr, recv_curr, is_laundering)
                            )
                            # Upsert Sender Account State
                            conn.execute(
                                """
                                INSERT INTO account_states (account_id, transaction_count, total_amount_paid, total_amount_received, amount_sum_sq, last_transaction_timestamp, updated_at)
                                VALUES (?, 1, ?, 0.0, ?, ?, CURRENT_TIMESTAMP)
                                ON CONFLICT (account_id) DO UPDATE SET
                                    transaction_count = account_states.transaction_count + 1,
                                    total_amount_paid = account_states.total_amount_paid + EXCLUDED.total_amount_paid,
                                    amount_sum_sq = account_states.amount_sum_sq + EXCLUDED.amount_sum_sq,
                                    last_transaction_timestamp = EXCLUDED.last_transaction_timestamp,
                                    updated_at = CURRENT_TIMESTAMP;
                                """,
                                (from_acct, amt_paid, amt_paid * amt_paid, ts_str)
                            )
                            # Upsert Receiver Account State
                            conn.execute(
                                """
                                INSERT INTO account_states (account_id, transaction_count, total_amount_paid, total_amount_received, amount_sum_sq, last_transaction_timestamp, updated_at)
                                VALUES (?, 0, 0.0, ?, 0.0, ?, CURRENT_TIMESTAMP)
                                ON CONFLICT (account_id) DO UPDATE SET
                                    total_amount_received = account_states.total_amount_received + EXCLUDED.total_amount_received,
                                    updated_at = CURRENT_TIMESTAMP;
                                """,
                                (to_acct, amt_recv, ts_str)
                            )
                except Exception as e:
                    if self.db.engine_type == "postgresql":
                        logger.error(f"PostgreSQL persist transaction failed: {e}")
                        raise RuntimeError(f"PostgreSQL persist failure: {e}") from e
                    logger.debug(f"Exception during add_transactions persist: {e}")

            # Update in-memory fallback DataFrame
            if self._in_memory_df is None or self._in_memory_df.empty:
                self._in_memory_df = local_df.copy()
            else:
                self._in_memory_df = pd.concat([self._in_memory_df, local_df], ignore_index=True)

            if "transaction_key" in self._in_memory_df.columns:
                self._in_memory_df = self._in_memory_df.drop_duplicates(subset=["transaction_key"], keep="last")

    def clear(self) -> None:
        """Clears in-memory transaction history and local test database state."""
        with self._lock:
            if self._in_memory_df is not None:
                self._in_memory_df = self._in_memory_df.iloc[0:0]
            else:
                self._in_memory_df = pd.DataFrame()

            try:
                conn = self.db.connect()
                if self.db.engine_type == "postgresql":
                    with conn.cursor() as cur:
                        cur.execute("TRUNCATE TABLE transaction_history, account_states;")
                    conn.commit()
                else:
                    conn.execute("DELETE FROM transaction_history;")
                    conn.execute("DELETE FROM account_states;")
            except Exception:
                pass


