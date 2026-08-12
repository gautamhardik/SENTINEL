"""
Script for Stage 2 (Profiling) and Stage 3 (Polars Streaming Cleaning & Validation Gate)
for the 16.7 GB LI-Large dataset.
"""
import json
import os
import sys
import time

import polars as pl

# Ensure UTF-8 output encoding on Windows console
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("=" * 60)
    print("STAGE 2: DATASET PROFILING & STAGE 3: CLEANING (LI-LARGE)")
    print("=" * 60)

    start_time = time.time()
    raw_trans_path = "data/raw/LI-Large_Trans.csv"
    output_dir = "data/cleaned"
    os.makedirs(output_dir, exist_ok=True)
    cleaned_parquet_path = os.path.join(output_dir, "transactions_clean.parquet")

    column_names = [
        "Timestamp", "From_Bank", "From_Account", "To_Bank", "To_Account",
        "Amount_Received", "Receiving_Currency", "Amount_Paid", "Payment_Currency",
        "Payment_Format", "Is_Laundering"
    ]

    print(f"Scanning raw transaction file: {raw_trans_path}...")
    lf = pl.scan_csv(
        raw_trans_path,
        has_header=True,
        new_columns=column_names,
        low_memory=True
    )

    # 1. Stage 2 Profiling using Polars lazy aggregation
    print("\n--- STAGE 2: DATASET PROFILING ---")

    # Compute profile metrics lazily
    profile_exprs = [
        pl.len().alias("total_rows"),
        pl.col("Is_Laundering").sum().alias("laundering_count"),
        pl.col("Timestamp").min().alias("min_timestamp"),
        pl.col("Timestamp").max().alias("max_timestamp"),
        pl.col("From_Account").n_unique().alias("unique_senders"),
        pl.col("To_Account").n_unique().alias("unique_receivers"),
        pl.col("From_Bank").n_unique().alias("unique_from_banks"),
        pl.col("To_Bank").n_unique().alias("unique_to_banks"),
    ]

    profile_res = lf.select(profile_exprs).collect()
    total_rows = profile_res["total_rows"][0]
    laundering_count = profile_res["laundering_count"][0]
    min_ts = profile_res["min_timestamp"][0]
    max_ts = profile_res["max_timestamp"][0]
    unique_senders = profile_res["unique_senders"][0]
    unique_receivers = profile_res["unique_receivers"][0]
    unique_from_banks = profile_res["unique_from_banks"][0]
    unique_to_banks = profile_res["unique_to_banks"][0]
    laundering_pct = (laundering_count / total_rows) * 100 if total_rows > 0 else 0.0

    print(f"Total Rows: {total_rows:,}")
    print(f"Laundering Count: {laundering_count:,} ({laundering_pct:.4f}%)")
    print(f"Timestamp Range: {min_ts} to {max_ts}")
    print(f"Unique Senders: {unique_senders:,}")
    print(f"Unique Receivers: {unique_receivers:,}")
    print(f"Unique Banks (From/To): {unique_from_banks:,} / {unique_to_banks:,}")

    # Payment format distribution
    fmt_dist = lf.group_by("Payment_Format").len().collect()
    print("\nPayment Format Distribution:")
    print(fmt_dist)

    # Save profile summary JSON
    profile_summary = {
        "dataset": "LI-Large",
        "total_rows": int(total_rows),
        "laundering_count": int(laundering_count),
        "laundering_pct": float(laundering_pct),
        "min_timestamp": str(min_ts),
        "max_timestamp": str(max_ts),
        "unique_senders": int(unique_senders),
        "unique_receivers": int(unique_receivers),
        "payment_format_counts": {row["Payment_Format"]: int(row["len"]) for row in fmt_dist.to_dicts()}
    }
    with open(os.path.join(output_dir, "dataset_profile.json"), "w") as f:
        json.dump(profile_summary, f, indent=2)

    # 2. Stage 3: Polars Stream Cleaning & Parquet Export
    print("\n--- STAGE 3: DATA CLEANING & VALIDATION GATE ---")
    print("Parsing timestamps, downcasting types, and generating TransactionIDs...")

    cleaned_lf = lf.with_columns([
        pl.concat_str([pl.lit("TX_"), pl.int_range(1, pl.len() + 1).cast(pl.Utf8)]).alias("TransactionID"),
        pl.col("Timestamp").str.to_datetime(format="%Y/%m/%d %H:%M", strict=False).alias("Timestamp"),
        pl.col("Amount_Paid").cast(pl.Float64).alias("Amount_Paid"),
        pl.col("Amount_Received").cast(pl.Float64).alias("Amount_Received"),
        pl.col("Is_Laundering").cast(pl.Int8).alias("Is_Laundering"),
        pl.col("From_Bank").cast(pl.Int32).alias("From_Bank"),
        pl.col("To_Bank").cast(pl.Int32).alias("To_Bank")
    ])

    print(f"Streaming cleaned dataset to {cleaned_parquet_path}...")
    cleaned_lf.sink_parquet(cleaned_parquet_path, compression="zstd")

    # Validation Gate
    print("\nRunning Validation Gate checks on clean parquet...")
    clean_check_lf = pl.scan_parquet(cleaned_parquet_path)
    val_res = clean_check_lf.select([
        pl.len().alias("clean_rows"),
        pl.col("TransactionID").n_unique().alias("unique_tx_ids"),
        (pl.col("Amount_Paid") < 0).sum().alias("negative_amounts"),
        pl.col("Timestamp").null_count().alias("null_timestamps")
    ]).collect()

    clean_rows = val_res["clean_rows"][0]
    unique_tx_ids = val_res["unique_tx_ids"][0]
    negative_amounts = val_res["negative_amounts"][0]
    null_timestamps = val_res["null_timestamps"][0]

    print(f"Clean Rows: {clean_rows:,} (Expected: {total_rows:,})")
    print(f"Unique Transaction IDs: {unique_tx_ids:,}")
    print(f"Negative Amounts Count: {negative_amounts}")
    print(f"Null Timestamps Count: {null_timestamps}")

    assert clean_rows == total_rows, f"Row count mismatch! {clean_rows} vs {total_rows}"
    assert unique_tx_ids == total_rows, "Duplicate Transaction IDs detected!"
    assert negative_amounts == 0, "Negative amounts detected!"
    assert null_timestamps == 0, "Unparsed null timestamps detected!"

    print("\n✅ STAGE 2 & STAGE 3 PASSED VALIDATION GATE!")
    print(f"Elapsed Time: {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    main()
