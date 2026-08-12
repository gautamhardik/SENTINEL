"""
Main Warehouse ETL Pipeline Orchestrator Class with Atomic Transaction Management & Stage Timings.
"""
import json
import time
from pathlib import Path
from typing import Any, Dict, NamedTuple

import polars as pl

from src.warehouse.database import CLEAN_DATA_PATH, DOCS_DIR, SQL_DIR, WarehouseConnection
from src.warehouse.etl_engine import WarehouseETLEngine
from src.warehouse.exceptions import ConnectionError
from src.warehouse.logger import SQLRunner, get_warehouse_logger
from src.warehouse.metadata import generate_pipeline_metadata
from src.warehouse.validator import WarehouseAudit, WarehouseValidator


class WarehouseETLResults(NamedTuple):
    connection_status: bool
    dimension_stats: Dict[str, Any]
    fact_stats: Dict[str, Any]
    validation_results: Dict[str, Any]
    audit_log: Dict[str, Any]
    metadata: Dict[str, Any]
    stage_timings: Dict[str, float]
    summary_df: pl.DataFrame


class WarehouseETLPipeline:
    """
    Orchestrates full Data Warehouse ETL pipeline with explicit BEGIN / COMMIT / ROLLBACK transaction safety:
    BEGIN -> Setup Schemas -> Load Dimensions -> Load Facts -> Validate -> Audit -> COMMIT (or ROLLBACK on failure).
    """
    def __init__(self, data_path: Path = CLEAN_DATA_PATH, engine_type: str = "duckdb"):
        self.data_path = Path(data_path)
        self.db_conn = WarehouseConnection(engine_type=engine_type)
        self.logger = get_warehouse_logger()

    def run(self) -> WarehouseETLResults:
        start_time = time.time()
        stage_timings: Dict[str, float] = {}
        self.logger.info("Starting Transaction-Safe Warehouse ETL Pipeline...")

        # 1. Connection Test
        t0 = time.time()
        conn_ok = self.db_conn.test_connection()
        if not conn_ok:
            raise ConnectionError("Failed to connect to Data Warehouse engine.")
        stage_timings["1_connection_test"] = round(time.time() - t0, 3)

        # 2. Ingest Clean Parquet
        t1 = time.time()
        self.logger.info(f"Ingesting clean dataset from {self.data_path}")
        df = pl.read_parquet(self.data_path)
        stage_timings["2_read_parquet"] = round(time.time() - t1, 3)

        conn = self.db_conn.connect()
        is_pg = self.db_conn.engine_type == "postgresql"

        try:
            # Transaction BEGIN Block
            if is_pg:
                with conn.cursor() as cur:
                    cur.execute("BEGIN;")
            else:
                conn.execute("BEGIN TRANSACTION;")

            # 3. Setup Schemas & Views
            t2 = time.time()
            runner = SQLRunner(self.db_conn)
            runner.execute_file(SQL_DIR / "01_schema.sql")
            runner.execute_file(SQL_DIR / "02_views.sql")
            stage_timings["3_schema_setup"] = round(time.time() - t2, 3)

            # 4. Load Dimensions & Facts via Vectorized Join Engine
            engine = WarehouseETLEngine(self.db_conn)
            dim_stats, dim_duration = engine.load_dimensions(df)
            stage_timings["4_dimension_loading"] = dim_duration

            fact_stats, fact_duration = engine.load_fact(df)
            stage_timings["5_fact_loading"] = fact_duration

            # 5. Validate Warehouse Integrity
            validator = WarehouseValidator(self.db_conn)
            val_results, val_duration = validator.validate_warehouse()
            stage_timings["6_integrity_validation"] = val_duration

            # Audit Trail Logging
            duration = round(time.time() - start_time, 2)
            auditor = WarehouseAudit(self.db_conn)
            audit_log = auditor.log_pipeline_run(
                pipeline_name="WarehouseETLPipeline",
                status=val_results.get("validation_status", "PASSED"),
                rows_extracted=df.height,
                rows_inserted=fact_stats.get("total_inserted", 0),
                duration_sec=duration
            )

            # Commit Transaction if all steps succeeded
            if is_pg:
                with conn.cursor() as cur:
                    cur.execute("COMMIT;")
                self.logger.info("ETL Transaction committed successfully.")
            else:
                conn.execute("COMMIT;")
                self.logger.info("ETL Transaction committed successfully.")

            duration = round(time.time() - start_time, 3)
            metadata_json_path = DOCS_DIR / "ETL_Pipeline_Metadata.json"
            metadata = generate_pipeline_metadata(
                metadata_json_path, df.height, self.db_conn.engine_type, duration, stage_timings
            )

            # 7. Export Audit Log
            audit_json_path = DOCS_DIR / "ETL_Audit.json"
            with open(audit_json_path, "w", encoding="utf-8") as f:
                json.dump(audit_log, f, indent=2)

            summary_df = pl.DataFrame([
                {"Stage": "1. Database Connection", "Status": "PASSED", "Timing (sec)": f"{stage_timings.get('1_connection_test', 0.0)}s", "Details": f"Engine: {self.db_conn.engine_type.upper()}"},
                {"Stage": "2. Dimension Loading", "Status": "PASSED", "Timing (sec)": f"{stage_timings.get('4_dimension_loading', 0.0)}s", "Details": f"Loaded {len(dim_stats)} dimension tables"},
                {"Stage": "3. Fact Table Loading", "Status": "PASSED", "Timing (sec)": f"{stage_timings.get('5_fact_loading', 0.0)}s", "Details": f"{fact_stats.get('total_inserted', 0):,} records inserted"},
                {"Stage": "4. Warehouse Validation", "Status": val_results.get('validation_status'), "Timing (sec)": f"{stage_timings.get('6_integrity_validation', 0.0)}s", "Details": f"{val_results.get('orphan_from_account_keys')} orphan FKs"},
                {"Stage": "5. Audit & Metadata", "Status": "PASSED", "Timing (sec)": f"{duration}s", "Details": f"Run ID: {audit_log['run_id']} | {metadata['throughput_rows_per_sec']} rows/sec"}
            ])

            self.logger.info("Warehouse ETL Pipeline completed successfully.")
            return WarehouseETLResults(
                connection_status=conn_ok,
                dimension_stats=dim_stats,
                fact_stats=fact_stats,
                validation_results=val_results,
                audit_log=audit_log,
                metadata=metadata,
                stage_timings=stage_timings,
                summary_df=summary_df
            )
        except Exception as e:
            if is_pg:
                with conn.cursor() as cur:
                    cur.execute("ROLLBACK;")
            else:
                try:
                    conn.execute("ROLLBACK;")
                except Exception:
                    pass
            self.logger.error(f"ETL Transaction failed and was rolled back: {e}")
            raise e
        finally:
            self.db_conn.close()
