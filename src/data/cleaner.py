"""
Data cleaning and data optimization transformation module with pure helper functions and decision logging.
"""
from typing import Any, Dict, List, Tuple

import polars as pl

from src.config.data_config import COLUMN_RENAMING_MAP, EXPECTED_DATETIME_FORMAT, OUTLIER_IQR_FACTOR


def _normalize_column_names(df: pl.DataFrame) -> Tuple[pl.DataFrame, Dict[str, Any]]:
    """Helper 1: Normalizes column names using COLUMN_RENAMING_MAP config."""
    # Apply explicit config map first, then sanitize remainder to snake_case
    rename_dict = {}
    for col in df.columns:
        if col in COLUMN_RENAMING_MAP:
            rename_dict[col] = COLUMN_RENAMING_MAP[col]
        else:
            rename_dict[col] = col.strip().replace(" ", "_").replace(".", "_")

    df_clean = df.rename(rename_dict)
    log_entry = {
        "Step": "1. Normalize Column Names",
        "Rows Affected": len(rename_dict),
        "Action": "Converted to snake_case & mapped headers via config",
        "Reason": "Ensures SQL and Python reference consistency"
    }
    return df_clean, log_entry


def _assign_transaction_ids(df: pl.DataFrame) -> Tuple[pl.DataFrame, Dict[str, Any]]:
    """Helper 2: Assigns unique sequence TransactionIDs if missing."""
    if "TransactionID" not in df.columns:
        df = df.with_columns(
            pl.concat_str([pl.lit("TX_"), pl.int_range(1, df.height + 1).cast(pl.Utf8)]).alias("TransactionID")
        )
    cols = ["TransactionID"] + [c for c in df.columns if c != "TransactionID"]
    df = df.select(cols)
    log_entry = {
        "Step": "2. Assign TransactionID",
        "Rows Affected": df.height,
        "Action": "Generated sequence TransactionIDs",
        "Reason": "Guarantees primary key uniqueness across pipeline"
    }
    return df, log_entry


def _trim_strings(df: pl.DataFrame) -> Tuple[pl.DataFrame, Dict[str, Any]]:
    """Helper 3: Strips whitespace from string columns."""
    string_cols = [c for c in df.columns if df[c].dtype == pl.Utf8]
    exprs = [pl.col(c).str.strip_chars().alias(c) for c in string_cols]
    df = df.with_columns(exprs)
    log_entry = {
        "Step": "3. Trim Whitespace",
        "Rows Affected": f"{len(string_cols)} columns",
        "Action": "Stripped leading & trailing whitespace",
        "Reason": "Prevents join mismatches and aggregation errors"
    }
    return df, log_entry


def _parse_datetime(df: pl.DataFrame) -> Tuple[pl.DataFrame, Dict[str, Any]]:
    """Helper 4: Parses string timestamps to Datetime ISO."""
    if "Timestamp" in df.columns and df["Timestamp"].dtype == pl.Utf8:
        df = df.with_columns(
            pl.col("Timestamp").str.to_datetime(format=EXPECTED_DATETIME_FORMAT, strict=False).alias("Timestamp")
        )
    log_entry = {
        "Step": "4. Cast Datetime",
        "Rows Affected": df.height,
        "Action": f"Parsed string timestamps using {EXPECTED_DATETIME_FORMAT}",
        "Reason": "Enables temporal windowing and time-series feature engineering"
    }
    return df, log_entry


def _remove_duplicates(df: pl.DataFrame, initial_rows: int) -> Tuple[pl.DataFrame, Dict[str, Any], int]:
    """Helper 5: Removes exact duplicate rows."""
    df_clean = df.unique()
    removed_dups = initial_rows - df_clean.height
    log_entry = {
        "Step": "5. Remove Duplicates",
        "Rows Affected": removed_dups,
        "Action": "Pruned identical transaction rows",
        "Reason": "Eliminates double-counted logging artifacts"
    }
    return df_clean, log_entry, removed_dups


def _flag_amount_outliers(df: pl.DataFrame) -> Tuple[pl.DataFrame, Dict[str, Any]]:
    """Helper 6: Flags extreme monetary outliers using config IQR factor."""
    outliers_count = 0
    if "Amount_Paid" in df.columns:
        q1_val = df["Amount_Paid"].quantile(0.25)
        q3_val = df["Amount_Paid"].quantile(0.75)
        q1 = q1_val if q1_val is not None else 0.0
        q3 = q3_val if q3_val is not None else 0.0
        iqr = q3 - q1
        upper_bound = q3 + OUTLIER_IQR_FACTOR * iqr

        outliers_count = df.filter(pl.col("Amount_Paid") > upper_bound).height
        df = df.with_columns(
            (pl.col("Amount_Paid") > upper_bound).cast(pl.Int8).alias("Is_Amount_Outlier_Flag")
        )
    log_entry = {
        "Step": "6. Flag Amount Outliers",
        "Rows Affected": outliers_count,
        "Action": f"Added Is_Amount_Outlier_Flag (IQR > {OUTLIER_IQR_FACTOR})",
        "Reason": "Preserves extreme transaction amounts as potential fraud signals"
    }
    return df, log_entry


def _optimize_memory(df: pl.DataFrame) -> Tuple[pl.DataFrame, Dict[str, Any]]:
    """Helper 7: Downcasts integers for memory optimization."""
    int_cols = [c for c in df.columns if df[c].dtype == pl.Int64]
    downcast_exprs = []
    for c in int_cols:
        if c in ["Is_Laundering", "Is_Amount_Outlier_Flag"]:
            downcast_exprs.append(pl.col(c).cast(pl.Int8))
        else:
            downcast_exprs.append(pl.col(c).cast(pl.Int32))
    df = df.with_columns(downcast_exprs)
    log_entry = {
        "Step": "7. Downcast Integers",
        "Rows Affected": len(int_cols),
        "Action": "Casted Int64 identifiers/flags to Int32/Int8",
        "Reason": "Optimizes memory footprint for high-throughput SQL & ML pipeline"
    }
    return df, log_entry


def clean_transaction_data(df: pl.DataFrame) -> Tuple[pl.DataFrame, Dict[str, Any], pl.DataFrame]:
    """
    Orchestrates pure helper functions to clean and optimize raw transaction dataframe.
    """
    initial_rows = df.height
    initial_mem = df.estimated_size()
    decision_log: List[Dict[str, Any]] = []

    # Execute modular pure helper steps
    df_clean, log1 = _normalize_column_names(df)
    decision_log.append(log1)

    df_clean, log2 = _assign_transaction_ids(df_clean)
    decision_log.append(log2)

    df_clean, log3 = _trim_strings(df_clean)
    decision_log.append(log3)

    df_clean, log4 = _parse_datetime(df_clean)
    decision_log.append(log4)

    df_clean, log5, removed_dups = _remove_duplicates(df_clean, initial_rows)
    decision_log.append(log5)

    df_clean, log6 = _flag_amount_outliers(df_clean)
    decision_log.append(log6)

    df_clean, log7 = _optimize_memory(df_clean)
    decision_log.append(log7)

    final_mem = df_clean.estimated_size()
    mem_reduction_pct = round(((initial_mem - final_mem) / initial_mem) * 100, 2) if initial_mem > 0 else 0.0

    metrics = {
        "initial_rows": initial_rows,
        "final_rows": df_clean.height,
        "removed_duplicates": removed_dups,
        "initial_memory_bytes": initial_mem,
        "final_memory_bytes": final_mem,
        "memory_reduction_pct": mem_reduction_pct
    }

    return df_clean, metrics, pl.DataFrame(decision_log)
