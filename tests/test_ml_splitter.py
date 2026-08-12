"""
Unit tests for chronological time-series data splitting logic.
"""
from datetime import datetime, timedelta

import polars as pl


def test_chronological_split():
    base_time = datetime(2026, 1, 1, 10, 0, 0)
    data = [
        {"Timestamp": base_time + timedelta(minutes=i), "Amount_Paid": float(i * 10), "Is_Laundering": i % 2}
        for i in range(20)
    ]
    df = pl.DataFrame(data).sort("Timestamp")

    n_total = df.height
    n_train = int(n_total * 0.70)
    n_val = int(n_total * 0.15)

    df_train = df[:n_train]
    df_val = df[n_train:n_train + n_val]
    df_test = df[n_train + n_val:]

    assert df_train.height + df_val.height + df_test.height == 20
    assert df_train["Timestamp"].max() <= df_val["Timestamp"].min()
    assert df_val["Timestamp"].max() <= df_test["Timestamp"].min()
