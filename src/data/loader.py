"""
Data loader module using Polars with eager and lazy loading support.
"""
from pathlib import Path
from typing import Union

import polars as pl


def load_transactions(file_path: Union[str, Path], lazy: bool = False) -> Union[pl.DataFrame, pl.LazyFrame]:
    """
    Loads raw transaction dataset from parquet or csv file format.
    Supports both Eager (pl.DataFrame) and Lazy (pl.LazyFrame) execution modes.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Raw data file not found at: {file_path}")

    if file_path.suffix == ".parquet":
        return pl.scan_parquet(file_path) if lazy else pl.read_parquet(file_path)
    elif file_path.suffix == ".csv":
        return pl.scan_csv(file_path) if lazy else pl.read_csv(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")
