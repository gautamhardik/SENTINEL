"""
Data Access Abstraction Layer for Enterprise Fraud Detection Platform.
Provides Repository pattern interfaces to decouple storage/data warehouse access from feature engineering pipelines.
"""
from typing import Optional

import polars as pl

from src.warehouse.database import DB_ENGINE_TYPE, WarehouseConnection
from src.warehouse.logger import get_warehouse_logger


class WarehouseRepository:
    """
    Data Repository handling warehouse data extraction for Feature Engineering & ML workloads.
    Enforces strict temporal ordering safeguards.
    """
    def __init__(self, db_conn: Optional[WarehouseConnection] = None):
        self.db_conn = db_conn if db_conn is not None else WarehouseConnection(engine_type=DB_ENGINE_TYPE)
        self.logger = get_warehouse_logger("WarehouseRepository")

    def load_transactions(self, limit: Optional[int] = None) -> pl.DataFrame:
        """
        Loads fact and dimension records from Data Warehouse sorted strictly by timestamp.
        Asserts temporal non-decreasing sequence to prevent lookahead leakage.
        Returns a Polars DataFrame.
        """
        self.logger.info("Connecting to Data Warehouse via WarehouseRepository...")
        conn = self.db_conn.connect()
        limit_clause = f"LIMIT {limit}" if limit else ""
        query = f"""
            SELECT 
                f.transaction_key,
                f.transaction_id,
                f.time_key,
                t.full_timestamp AS Timestamp,
                f.from_bank_key,
                b1.bank_id AS From_Bank,
                f.from_account_key,
                a1.account_number AS From_Account,
                f.to_bank_key,
                b2.bank_id AS To_Bank,
                f.to_account_key,
                a2.account_number AS To_Account,
                f.payment_format_key,
                fmt.format_name AS Payment_Format,
                f.payment_currency_key,
                c1.currency_code AS Payment_Currency,
                f.receiving_currency_key,
                c2.currency_code AS Receiving_Currency,
                f.amount_paid AS Amount_Paid,
                f.amount_received AS Amount_Received,
                f.is_amount_outlier,
                f.is_laundering
            FROM fact_transactions f
            JOIN dim_time t ON f.time_key = t.time_key
            JOIN dim_bank b1 ON f.from_bank_key = b1.bank_key
            JOIN dim_bank b2 ON f.to_bank_key = b2.bank_key
            JOIN dim_account a1 ON f.from_account_key = a1.account_key
            JOIN dim_account a2 ON f.to_account_key = a2.account_key
            JOIN dim_payment_format fmt ON f.payment_format_key = fmt.payment_format_key
            JOIN dim_currency c1 ON f.payment_currency_key = c1.currency_key
            JOIN dim_currency c2 ON f.receiving_currency_key = c2.currency_key
            ORDER BY t.full_timestamp ASC, f.transaction_key ASC
            {limit_clause};
        """
        try:
            res = conn.execute(query).fetchall()
            cols = [desc[0] for desc in conn.description]
            df = pl.DataFrame(res, schema=cols, orient="row")
            df = df.with_columns([
                pl.col("Timestamp").cast(pl.Datetime),
                pl.col("Amount_Paid").cast(pl.Float64),
                pl.col("Amount_Received").cast(pl.Float64)
            ])

            # Temporal Ordering Safeguard Assertion
            if not df["Timestamp"].is_sorted():
                raise ValueError("Temporal Ordering Failure: Data Warehouse transactions are not sorted non-decreasingly by Timestamp!")

            self.logger.info(f"Loaded {df.height:,} transactions from Data Warehouse via Repository (Temporal Ordering Verified).")
            return df
        finally:
            self.db_conn.close()
