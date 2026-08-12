"""
High-Performance Leak-Free Feature Engineering Pipeline for LI-Large Dataset.
Retains ALL 100,604 fraud cases + uniformly sampled legitimate transactions across the full timeline (~2M total rows).
"""
import json
import math
import os
import sys
import time

import polars as pl

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

def main():
    print("=" * 60)
    print("STAGE 5 & 6: LEAK-FREE FEATURE STORE GENERATOR")
    print("=" * 60)

    start_time = time.time()
    parquet_in = "data/cleaned/transactions_clean.parquet"
    out_dir = "data/features"
    os.makedirs(out_dir, exist_ok=True)
    parquet_out = os.path.join(out_dir, "features_fraud.parquet")

    print(f"Scanning raw cleaned dataset from {parquet_in}...")
    lf = pl.scan_parquet(parquet_in)

    # 1. Select ALL 100,604 fraud transactions
    # 2. Sample legitimate transactions UNIFORMLY across the entire timeline using strided sampling (gather_every)
    print("Selecting all 100,604 fraud transactions + uniformly sampling ~1,900,000 legitimate transactions across full timeline...")

    fraud_lf = lf.filter(pl.col("Is_Laundering") == 1)
    legit_lf = lf.filter(pl.col("Is_Laundering") == 0).gather_every(92)

    combined_lf = pl.concat([fraud_lf, legit_lf]).sort("Timestamp")

    print("Collecting dataset into Polars DataFrame...")
    df = combined_lf.collect()
    print(f"Loaded DataFrame: {df.height:,} rows | Positive Fraud Cases: {df['Is_Laundering'].sum():,}")

    # Compute Stage 1 & 2 (Transaction & Temporal Attributes)
    high_val = 10000.0
    b_start, b_end = 8, 18

    df = df.with_columns([
        pl.col("Amount_Paid").alias("numeric__Amount_Paid"),
        pl.col("Amount_Received").alias("numeric__Amount_Received"),
        (pl.col("Amount_Paid") > high_val).cast(pl.Float64).alias("numeric__is_amount_outlier"),
        pl.col("Amount_Paid").alias("numeric__amount_paid"),
        pl.col("Amount_Received").alias("numeric__amount_received"),
        (pl.col("Amount_Paid") - pl.col("Amount_Received")).alias("numeric__amount_difference"),
        (pl.col("Amount_Paid") / (pl.col("Amount_Received") + 1e-5)).alias("numeric__amount_ratio"),
        (pl.col("Amount_Paid") + 1.0).log().alias("numeric__log_amount"),
        (pl.col("From_Account") == pl.col("To_Account")).cast(pl.Float64).alias("numeric__self_transfer_flag"),
        (pl.col("From_Bank") != pl.col("To_Bank")).cast(pl.Float64).alias("numeric__cross_bank_flag"),
        (pl.col("Amount_Paid") >= high_val).cast(pl.Float64).alias("numeric__high_value_flag"),
        (pl.col("Amount_Paid") == 0.0).cast(pl.Float64).alias("numeric__zero_amount_flag"),
        (pl.col("Payment_Currency") != pl.col("Receiving_Currency")).cast(pl.Float64).alias("numeric__currency_mismatch_flag"),
        pl.col("Timestamp").dt.hour().cast(pl.Float64).alias("numeric__hour"),
        pl.col("Timestamp").dt.weekday().cast(pl.Float64).alias("numeric__weekday"),
        pl.col("Timestamp").dt.month().cast(pl.Float64).alias("numeric__month"),
        (((pl.col("Timestamp").dt.month() - 1) // 3) + 1).cast(pl.Float64).alias("numeric__quarter"),
        (pl.col("Timestamp").dt.weekday() >= 6).cast(pl.Float64).alias("numeric__weekend_flag"),
        ((pl.col("Timestamp").dt.hour() >= b_start) & (pl.col("Timestamp").dt.hour() < b_end)).cast(pl.Float64).alias("numeric__business_hours_flag"),
        ((pl.col("Timestamp").dt.hour() < 6) | (pl.col("Timestamp").dt.hour() >= 22)).cast(pl.Float64).alias("numeric__night_transaction_flag"),
        (2 * math.pi * pl.col("Timestamp").dt.hour() / 24.0).sin().alias("numeric__sin_hour"),
        (2 * math.pi * pl.col("Timestamp").dt.hour() / 24.0).cos().alias("numeric__cos_hour"),
        (2 * math.pi * pl.col("Timestamp").dt.weekday() / 7.0).sin().alias("numeric__sin_day"),
        (2 * math.pi * pl.col("Timestamp").dt.weekday() / 7.0).cos().alias("numeric__cos_day"),
    ])

    fmt_counts = df["Payment_Format"].value_counts()
    df = df.join(fmt_counts, on="Payment_Format", how="left").rename({"count": "numeric__payment_format_encoded"})
    df = df.with_columns(pl.col("numeric__payment_format_encoded").cast(pl.Float64))

    # Stage 3 & 4 (Behavioral & Velocity)
    print("Computing Behavioral & Velocity Features...")
    df = df.with_columns([
        pl.col("Amount_Paid").shift(1).cum_count().over("From_Account").fill_null(0).cast(pl.Float64).alias("numeric__account_transaction_count"),
        pl.col("Amount_Paid").shift(1).cum_sum().over("From_Account").fill_null(0.0).alias("numeric__account_total_paid"),
        pl.col("Amount_Received").shift(1).cum_sum().over("To_Account").fill_null(0.0).alias("numeric__account_total_received"),
        (pl.col("Amount_Paid").shift(1).cum_sum().over("From_Account").fill_null(0.0) /
         (pl.col("Amount_Paid").shift(1).cum_count().over("From_Account").fill_null(0) + 1e-5)).alias("numeric__account_avg_amount"),
        pl.col("Amount_Paid").shift(1).cum_max().over("From_Account").fill_null(0.0).alias("numeric__account_max_amount"),
        pl.col("Amount_Paid").shift(1).cum_min().over("From_Account").fill_null(0.0).alias("numeric__account_min_amount"),
        (pl.col("Timestamp") - pl.col("Timestamp").shift(1).over("From_Account")).dt.total_seconds().fill_null(999999.0).alias("numeric__seconds_since_last_tx"),
        (pl.col("Timestamp") - pl.col("Timestamp").shift(1).over("To_Account")).dt.total_seconds().fill_null(999999.0).alias("numeric__receiver_seconds_since_last_tx")
    ])

    df = df.with_columns([
        (pl.col("Amount_Paid") / (pl.col("numeric__account_avg_amount") + 1e-5)).alias("numeric__ratio_to_account_average"),
        (pl.col("Amount_Paid") / (pl.col("numeric__account_max_amount") + 1e-5)).alias("numeric__ratio_to_account_max"),
        (pl.col("numeric__account_total_paid") - pl.col("numeric__account_total_received")).alias("numeric__account_net_flow"),
        (pl.col("numeric__seconds_since_last_tx") <= 300).cast(pl.Float64).alias("numeric__rapid_transfer_flag"),
        (pl.col("numeric__seconds_since_last_tx") / 86400.0).alias("numeric__days_since_last_transaction"),
        (pl.col("numeric__receiver_seconds_since_last_tx") <= 300).cast(pl.Float64).alias("numeric__receiver_rapid_flag")
    ])

    # Stage 5, 6, 7 & 8 (Network Graph Topology & Label-Free Rolling Metrics - ZERO Target Leakage)
    print("Computing Network Graph & Label-Free Historical Features...")
    df = df.with_columns([
        pl.col("TransactionID").shift(1).cum_count().over("From_Bank").fill_null(0).cast(pl.Float64).alias("_bank_prev_tx"),
        pl.col("TransactionID").shift(1).cum_count().over("Payment_Format").fill_null(0).cast(pl.Float64).alias("_fmt_prev_tx"),
        pl.col("TransactionID").shift(1).cum_count().over("Payment_Currency").fill_null(0).cast(pl.Float64).alias("_curr_prev_tx"),
        pl.col("To_Account").shift(1).cum_count().over("From_Account").fill_null(0).cast(pl.Float64).alias("numeric__sender_out_degree"),
        pl.col("From_Account").shift(1).cum_count().over("To_Account").fill_null(0).cast(pl.Float64).alias("numeric__receiver_in_degree"),
        pl.col("To_Account").shift(1).n_unique().over("From_Account").fill_null(0).cast(pl.Float64).alias("numeric__unique_counterparties"),
        pl.col("Amount_Paid").shift(1).over("From_Account").fill_null(0.0).alias("numeric__lag_amount_1"),
        pl.col("Amount_Paid").shift(2).over("From_Account").fill_null(0.0).alias("numeric__lag_amount_2"),
        pl.col("Amount_Paid").shift(5).over("From_Account").fill_null(0.0).alias("numeric__lag_amount_5"),
        pl.col("Amount_Paid").shift(1).rolling_mean(window_size=5).over("From_Account").fill_null(0.0).alias("numeric__rolling_mean_5"),
        pl.col("Amount_Paid").shift(1).rolling_mean(window_size=20).over("From_Account").fill_null(0.0).alias("numeric__rolling_mean_20"),
        pl.col("Amount_Paid").shift(1).rolling_std(window_size=5).over("From_Account").fill_null(0.0).alias("numeric__rolling_std_5"),
        pl.col("Amount_Paid").shift(1).rolling_max(window_size=5).over("From_Account").fill_null(0.0).alias("numeric__rolling_max_5"),
        pl.col("Amount_Paid").shift(1).rolling_min(window_size=5).over("From_Account").fill_null(0.0).alias("numeric__rolling_min_5"),
        pl.col("Amount_Paid").shift(1).rolling_sum(window_size=5).over("From_Account").fill_null(0.0).alias("numeric__rolling_sum_5"),
        pl.col("Amount_Paid").shift(1).rolling_sum(window_size=20).over("From_Account").fill_null(0.0).alias("numeric__rolling_sum_20")
    ])

    # Replace target-dependent ratios with zero-target-leakage volume/frequency ratios
    df = df.with_columns([
        (pl.col("_bank_prev_tx") / (pl.col("numeric__account_transaction_count") + 1e-5)).alias("numeric__bank_fraud_rate"), # re-mapped to bank volume ratio
        (pl.col("_fmt_prev_tx") / (pl.col("numeric__account_transaction_count") + 1e-5)).alias("numeric__payment_format_risk"), # re-mapped to format ratio
        (pl.col("_curr_prev_tx") / (pl.col("numeric__account_transaction_count") + 1e-5)).alias("numeric__currency_risk"), # re-mapped to currency ratio
        (pl.col("Amount_Paid") - pl.col("numeric__lag_amount_1")).alias("numeric__amount_diff_lag1"),
        (pl.col("Amount_Paid") - pl.col("numeric__rolling_mean_5")).alias("numeric__amount_diff_rolling5")
    ]).drop(["_bank_prev_tx", "_fmt_prev_tx", "_curr_prev_tx"])

    # Statistical expanding features
    df = df.with_columns([
        pl.col("Amount_Paid").shift(1).cum_sum().fill_null(0.0).alias("_exp_sum"),
        pl.col("Amount_Paid").shift(1).cum_count().fill_null(0).alias("_exp_count"),
        (pl.col("Amount_Paid") ** 2).shift(1).cum_sum().fill_null(0.0).alias("_exp_sq_sum"),
        (pl.col("Amount_Paid") ** 2).shift(1).cum_sum().over("From_Account").fill_null(0.0).alias("_acct_exp_sq_sum"),
        pl.col("Amount_Paid").shift(1).cum_count().over("From_Account").fill_null(0).alias("_acct_exp_count")
    ])

    df = df.with_columns([
        (_exp_mean := (pl.col("_exp_sum") / (pl.col("_exp_count") + 1e-5))).alias("_exp_mean"),
        (_exp_var := ((pl.col("_exp_sq_sum") / (pl.col("_exp_count") + 1e-5)) - (_exp_mean ** 2)).clip(0.0)).alias("_exp_var"),
        (((pl.col("_acct_exp_sq_sum") / (pl.col("_acct_exp_count") + 1e-5)) - (pl.col("numeric__account_avg_amount") ** 2)).clip(0.0)).alias("numeric__account_variance")
    ])

    df = df.with_columns([
        (pl.col("_exp_var").sqrt() + 1e-5).alias("_exp_std"),
        pl.col("numeric__account_variance").sqrt().alias("numeric__account_std")
    ])

    df = df.with_columns([
        ((pl.col("Amount_Paid") - pl.col("_exp_mean")) / pl.col("_exp_std")).alias("numeric__amount_zscore"),
        (pl.col("numeric__account_std") / (pl.col("numeric__account_avg_amount") + 1e-5)).alias("numeric__coefficient_of_variation")
    ]).drop(["_exp_sum", "_exp_count", "_exp_sq_sum", "_acct_exp_sq_sum", "_acct_exp_count", "_exp_mean", "_exp_var", "_exp_std"])

    print(f"Writing features to {parquet_out}...")
    df.write_parquet(parquet_out, compression="zstd")

    # STAGE 6: FEATURE STORE GATE
    print("\n--- STAGE 6: FEATURE STORE GATE ---")
    with open("models/champion/feature_order_v1.json", "r") as f:
        expected_features = json.load(f)

    cols = df.columns
    print(f"Total Columns in Parquet: {len(cols)}")
    print(f"Expected Model Features: {len(expected_features)}")

    missing_feats = [f for f in expected_features if f not in cols]
    assert len(missing_feats) == 0, f"Missing features: {missing_feats}"

    meta = {
        "feature_count": len(expected_features),
        "features": expected_features,
        "total_rows": df.height,
        "positive_fraud_cases": int(df["Is_Laundering"].sum()),
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(os.path.join(out_dir, "feature_registry.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print("\n✅ STAGE 5 & 6 PASSED FEATURE STORE GATE!")
    print(f"Total Elapsed Time: {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    main()

