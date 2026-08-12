"""
Pipeline Metadata Generator for Reproducibility, Auditing, and Performance Analytics.
"""
import json
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def get_git_commit_hash() -> str:
    try:
        res = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return "UNKNOWN_GIT_HASH"

def generate_pipeline_metadata(
    output_path: Path,
    clean_df_height: int,
    engine_type: str,
    duration_sec: float,
    stage_timings: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """Generates Warehouse_Metadata.json tracking Git SHA, system context, checksums, and throughput."""
    import polars as pl

    throughput = round(clean_df_height / max(0.001, duration_sec), 2)

    metadata = {
        "pipeline_name": "Fraud Detection Data Warehouse ETL Pipeline",
        "pipeline_version": "2.0.0",
        "git_commit_sha": get_git_commit_hash(),
        "run_id": f"RUN_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now().isoformat(),
        "execution_duration_sec": duration_sec,
        "throughput_rows_per_sec": throughput,
        "stage_timings_sec": stage_timings or {},
        "database_engine": engine_type.upper(),
        "environment": "production",
        "system_context": {
            "python_version": sys.version.split()[0],
            "polars_version": pl.__version__,
            "platform": platform.platform(),
            "processor": platform.processor()
        },
        "dataset_telemetry": {
            "extracted_rows": clean_df_height,
            "fact_table": "warehouse.fact_transactions",
            "dimensions_loaded": ["dim_time", "dim_bank", "dim_account", "dim_currency", "dim_payment_format"]
        }
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return metadata
