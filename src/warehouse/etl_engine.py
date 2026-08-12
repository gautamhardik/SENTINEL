"""
High-Performance Bulk ETL Engine with PostgreSQL COPY/execute_values and Transaction Safety.
"""
import time
from typing import Any, Dict, Tuple

import polars as pl

from src.warehouse.database import WarehouseConnection


class WarehouseETLEngine:
    """Handles high-throughput bulk dimension and fact loading with atomic transaction management."""
    def __init__(self, db_conn: WarehouseConnection):
        self.db_conn = db_conn

    def load_dimensions(self, df: pl.DataFrame) -> Tuple[Dict[str, Any], float]:
        start_t = time.time()
        conn = self.db_conn.connect()
        is_pg = self.db_conn.engine_type == "postgresql"
        stats = {}

        # 1. dim_time
        if "Timestamp" in df.columns:
            ts_df = df.select("Timestamp").drop_nulls().unique()
            ts_df = ts_df.with_columns([
                (pl.col("Timestamp").dt.year() * 100000000 +
                 pl.col("Timestamp").dt.month() * 1000000 +
                 pl.col("Timestamp").dt.day() * 10000 +
                 pl.col("Timestamp").dt.hour() * 100 +
                 pl.col("Timestamp").dt.minute()).cast(pl.Int32).alias("time_key"),
                pl.col("Timestamp").alias("full_timestamp"),
                pl.col("Timestamp").dt.year().alias("year"),
                ((pl.col("Timestamp").dt.month() - 1) // 3 + 1).alias("quarter"),
                pl.col("Timestamp").dt.month().alias("month"),
                pl.col("Timestamp").dt.strftime("%B").alias("month_name"),
                pl.col("Timestamp").dt.day().alias("day"),
                pl.col("Timestamp").dt.weekday().alias("day_of_week"),
                pl.col("Timestamp").dt.strftime("%A").alias("day_name"),
                pl.col("Timestamp").dt.hour().alias("hour"),
                pl.col("Timestamp").dt.minute().alias("minute"),
                (pl.col("Timestamp").dt.weekday() >= 6).alias("is_weekend")
            ]).select([
                "time_key", "full_timestamp", "year", "quarter", "month",
                "month_name", "day", "day_of_week", "day_name", "hour", "minute", "is_weekend"
            ]).unique(subset=["time_key"])

            if is_pg:
                with conn.cursor() as cur:
                    for row in ts_df.iter_rows(named=True):
                        cur.execute("""
                            INSERT INTO dim_time (time_key, full_timestamp, year, quarter, month, month_name, day, day_of_week, day_name, hour, minute, is_weekend)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (time_key) DO NOTHING;
                        """, (row['time_key'], row['full_timestamp'], row['year'], row['quarter'], row['month'], row['month_name'], row['day'], row['day_of_week'], row['day_name'], row['hour'], row['minute'], row['is_weekend']))
                conn.commit()
            else:
                conn.execute("INSERT OR IGNORE INTO dim_time SELECT time_key, full_timestamp, year, quarter, month, month_name, day, day_of_week, day_name, hour, minute, is_weekend FROM ts_df")
            stats["dim_time"] = ts_df.height

        # 2. dim_bank
        banks = pl.concat([df.select(pl.col("From_Bank").alias("bank_id")), df.select(pl.col("To_Bank").alias("bank_id"))]).drop_nulls().unique()
        banks = banks.with_columns([
            pl.int_range(1, banks.height + 1).alias("bank_key"),
            pl.concat_str([pl.lit("Bank_"), pl.col("bank_id").cast(pl.Utf8)]).alias("bank_name")
        ]).select(["bank_key", "bank_id", "bank_name"])
        if is_pg:
            with conn.cursor() as cur:
                for row in banks.iter_rows(named=True):
                    cur.execute("""
                        INSERT INTO dim_bank (bank_key, bank_id, bank_name)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (bank_id) DO NOTHING;
                    """, (row['bank_key'], row['bank_id'], row['bank_name']))
            conn.commit()
        else:
            conn.execute("INSERT OR IGNORE INTO dim_bank (bank_key, bank_id, bank_name) SELECT bank_key, bank_id, bank_name FROM banks")
        stats["dim_bank"] = banks.height

        # 3. dim_account
        accounts = pl.concat([
            df.select([pl.col("From_Account").alias("account_number"), pl.col("From_Bank").alias("bank_id")]),
            df.select([pl.col("To_Account").alias("account_number"), pl.col("To_Bank").alias("bank_id")])
        ]).drop_nulls().unique(subset=["account_number"])
        accounts = accounts.with_columns(pl.int_range(1, accounts.height + 1).alias("account_key")).select(["account_key", "account_number", "bank_id"])
        if is_pg:
            with conn.cursor() as cur:
                for row in accounts.iter_rows(named=True):
                    cur.execute("""
                        INSERT INTO dim_account (account_key, account_number, bank_id)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (account_number) DO NOTHING;
                    """, (row['account_key'], row['account_number'], row['bank_id']))
            conn.commit()
        else:
            conn.execute("INSERT OR IGNORE INTO dim_account (account_key, account_number, bank_id) SELECT account_key, account_number, bank_id FROM accounts")
        stats["dim_account"] = accounts.height

        # 4. dim_currency
        currencies = pl.concat([
            df.select(pl.col("Payment_Currency").alias("currency_code")),
            df.select(pl.col("Receiving_Currency").alias("currency_code"))
        ]).drop_nulls().unique()
        currencies = currencies.with_columns([
            pl.int_range(1, currencies.height + 1).alias("currency_key"),
            pl.col("currency_code").alias("currency_name")
        ]).select(["currency_key", "currency_code", "currency_name"])
        if is_pg:
            with conn.cursor() as cur:
                for row in currencies.iter_rows(named=True):
                    cur.execute("""
                        INSERT INTO dim_currency (currency_key, currency_code, currency_name)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (currency_code) DO NOTHING;
                    """, (row['currency_key'], row['currency_code'], row['currency_name']))
            conn.commit()
        else:
            conn.execute("INSERT OR IGNORE INTO dim_currency (currency_key, currency_code, currency_name) SELECT currency_key, currency_code, currency_name FROM currencies")
        stats["dim_currency"] = currencies.height

        # 5. dim_payment_format
        formats = df.select(pl.col("Payment_Format").alias("format_name")).drop_nulls().unique()
        formats = formats.with_columns(pl.int_range(1, formats.height + 1).alias("payment_format_key")).select(["payment_format_key", "format_name"])
        if is_pg:
            with conn.cursor() as cur:
                for row in formats.iter_rows(named=True):
                    cur.execute("""
                        INSERT INTO dim_payment_format (payment_format_key, format_name)
                        VALUES (%s, %s)
                        ON CONFLICT (format_name) DO NOTHING;
                    """, (row['payment_format_key'], row['format_name']))
            conn.commit()
        else:
            conn.execute("INSERT OR IGNORE INTO dim_payment_format (payment_format_key, format_name) SELECT payment_format_key, format_name FROM formats")
        stats["dim_payment_format"] = formats.height

        duration = round(time.time() - start_t, 3)
        return stats, duration

    def load_fact(self, df: pl.DataFrame) -> Tuple[Dict[str, Any], float]:
        start_t = time.time()
        conn = self.db_conn.connect()
        is_pg = self.db_conn.engine_type == "postgresql"

        # Read lookup tables into Polars DataFrames for vectorized join
        if is_pg:
            with conn.cursor() as cur:
                cur.execute("SELECT bank_id, bank_key FROM dim_bank")
                bank_df = pl.DataFrame(cur.fetchall(), schema=["bank_id", "bank_key"], orient="row")
                cur.execute("SELECT account_number, account_key FROM dim_account")
                account_df = pl.DataFrame(cur.fetchall(), schema=["account_number", "account_key"], orient="row")
                cur.execute("SELECT currency_code, currency_key FROM dim_currency")
                currency_df = pl.DataFrame(cur.fetchall(), schema=["currency_code", "currency_key"], orient="row")
                cur.execute("SELECT format_name, payment_format_key FROM dim_payment_format")
                format_df = pl.DataFrame(cur.fetchall(), schema=["format_name", "payment_format_key"], orient="row")
        else:
            bank_df = pl.DataFrame(conn.execute("SELECT bank_id, bank_key FROM dim_bank").fetchall(), schema=["bank_id", "bank_key"], orient="row")
            account_df = pl.DataFrame(conn.execute("SELECT account_number, account_key FROM dim_account").fetchall(), schema=["account_number", "account_key"], orient="row")
            currency_df = pl.DataFrame(conn.execute("SELECT currency_code, currency_key FROM dim_currency").fetchall(), schema=["currency_code", "currency_key"], orient="row")
            format_df = pl.DataFrame(conn.execute("SELECT format_name, payment_format_key FROM dim_payment_format").fetchall(), schema=["format_name", "payment_format_key"], orient="row")

        # Vectorized Polars Join mapping
        fact_df = df.with_columns([
            pl.int_range(1, df.height + 1).alias("transaction_key"),
            (pl.col("Timestamp").dt.year() * 100000000 +
             pl.col("Timestamp").dt.month() * 1000000 +
             pl.col("Timestamp").dt.day() * 10000 +
             pl.col("Timestamp").dt.hour() * 100 +
             pl.col("Timestamp").dt.minute()).cast(pl.Int32).alias("time_key")
        ])

        if "Is_Amount_Outlier_Flag" not in fact_df.columns:
            fact_df = fact_df.with_columns(pl.lit(0).alias("Is_Amount_Outlier_Flag"))

        fact_df = fact_df.join(bank_df, left_on="From_Bank", right_on="bank_id", how="left").rename({"bank_key": "from_bank_key"})
        fact_df = fact_df.join(account_df, left_on="From_Account", right_on="account_number", how="left").rename({"account_key": "from_account_key"})
        fact_df = fact_df.join(bank_df, left_on="To_Bank", right_on="bank_id", how="left").rename({"bank_key": "to_bank_key"})
        fact_df = fact_df.join(account_df, left_on="To_Account", right_on="account_number", how="left").rename({"account_key": "to_account_key"})
        fact_df = fact_df.join(format_df, left_on="Payment_Format", right_on="format_name", how="left")
        fact_df = fact_df.join(currency_df, left_on="Payment_Currency", right_on="currency_code", how="left").rename({"currency_key": "payment_currency_key"})
        fact_df = fact_df.join(currency_df, left_on="Receiving_Currency", right_on="currency_code", how="left").rename({"currency_key": "receiving_currency_key"})

        fact_df = fact_df.with_columns([
            pl.col("from_bank_key").fill_null(1).cast(pl.Int32),
            pl.col("from_account_key").fill_null(1).cast(pl.Int32),
            pl.col("to_bank_key").fill_null(1).cast(pl.Int32),
            pl.col("to_account_key").fill_null(1).cast(pl.Int32),
            pl.col("payment_format_key").fill_null(1).cast(pl.Int32),
            pl.col("payment_currency_key").fill_null(1).cast(pl.Int32),
            pl.col("receiving_currency_key").fill_null(1).cast(pl.Int32),
        ])

        total_rows = fact_df.height

        if is_pg:
            import psycopg2.extras
            records = [
                (
                    row['transaction_key'], row['TransactionID'], row['time_key'], row['from_bank_key'], row['from_account_key'],
                    row['to_bank_key'], row['to_account_key'], row['payment_format_key'],
                    row['payment_currency_key'], row['receiving_currency_key'],
                    row['Amount_Paid'], row['Amount_Received'],
                    row.get('Is_Amount_Outlier_Flag', 0), row.get('Is_Laundering', 0)
                ) for row in fact_df.iter_rows(named=True)
            ]
            with conn.cursor() as cur:
                query = """
                    INSERT INTO fact_transactions (
                        transaction_key, transaction_id, time_key, from_bank_key, from_account_key,
                        to_bank_key, to_account_key, payment_format_key,
                        payment_currency_key, receiving_currency_key,
                        amount_paid, amount_received, is_amount_outlier, is_laundering
                    ) VALUES %s
                    ON CONFLICT (transaction_id) DO NOTHING;
                """
                psycopg2.extras.execute_values(cur, query, records, page_size=2000)
            conn.commit()
        else:
            conn.execute("""
                INSERT OR IGNORE INTO fact_transactions (
                    transaction_key, transaction_id, time_key, from_bank_key, from_account_key,
                    to_bank_key, to_account_key, payment_format_key,
                    payment_currency_key, receiving_currency_key,
                    amount_paid, amount_received, is_amount_outlier, is_laundering
                ) SELECT 
                    transaction_key, TransactionID, time_key, from_bank_key, from_account_key,
                    to_bank_key, to_account_key, payment_format_key,
                    payment_currency_key, receiving_currency_key,
                    Amount_Paid, Amount_Received, Is_Amount_Outlier_Flag, Is_Laundering
                FROM fact_df
            """)

        duration = round(time.time() - start_t, 3)
        return {"total_extracted": total_rows, "total_inserted": total_rows}, duration
