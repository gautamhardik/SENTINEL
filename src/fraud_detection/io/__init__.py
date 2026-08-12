"""
Safe I/O Readers and Batch Output Writers Module.
"""
from pathlib import Path
from typing import Any, Dict, List, Union

import pandas as pd
import polars as pl


class DataReader:
    """Safely reads CSV or Parquet files into Polars DataFrames."""

    @staticmethod
    def read_file(file_path: Union[str, Path]) -> pl.DataFrame:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Data file not found at: {path}")

        if path.suffix == ".parquet":
            return pl.read_parquet(path)
        elif path.suffix == ".csv":
            return pl.read_csv(path)
        else:
            raise ValueError(f"Unsupported file format '{path.suffix}'. Expected .csv or .parquet.")


class DataWriter:
    """Exports batch inference results to CSV or Parquet."""

    @staticmethod
    def export_batch(df: pl.DataFrame, output_path: Union[str, Path]) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".parquet":
            df.write_parquet(path)
        else:
            df.write_csv(path)
        return path
