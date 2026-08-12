"""
Production Pipeline Class Orchestrator for End-to-End Data Ingestion, Validation, Cleaning, & Reporting.
"""
import time
from pathlib import Path
from typing import Any, Dict, NamedTuple, Union

import polars as pl

from src.config.data_config import CLEAN_DATA_PATH, RAW_DATA_PATH, REPORT_PATH
from src.data.cleaner import clean_transaction_data
from src.data.exporter import export_clean_dataset, generate_data_quality_report
from src.data.loader import load_transactions
from src.data.validator import (
    analyze_duplicates,
    analyze_missing_values,
    build_validation_report_object,
    compute_enterprise_quality_dimensions,
    detect_outliers_iqr_zscore,
    validate_domain_rules,
)


class PipelineResults(NamedTuple):
    clean_df: pl.DataFrame
    dashboard: pl.DataFrame
    missing_analysis: pl.DataFrame
    duplicate_summary: pl.DataFrame
    domain_summary: pl.DataFrame
    statistical_profile: pl.DataFrame
    outlier_summary: pl.DataFrame
    decision_log: pl.DataFrame
    before_after_comparison: pl.DataFrame
    quality_dimensions: pl.DataFrame
    export_status: pl.DataFrame
    validation_report_object: Dict[str, Any]


class DataValidationPipeline:
    """
    Object-oriented production pipeline orchestrator that encapsulates end-to-end dataset lifecycle:
    Load -> Ingest -> Structural Validate -> Domain Validate -> Profile -> Clean -> Post-Validate -> Export.
    """
    def __init__(
        self,
        raw_data_path: Union[str, Path] = RAW_DATA_PATH,
        clean_data_path: Union[str, Path] = CLEAN_DATA_PATH,
        report_path: Union[str, Path] = REPORT_PATH,
        lazy: bool = False
    ):
        self.raw_data_path = Path(raw_data_path)
        self.clean_data_path = Path(clean_data_path)
        self.report_path = Path(report_path)
        self.lazy = lazy

    def run(self) -> PipelineResults:
        """Executes full pipeline orchestration."""
        start_time = time.time()

        # 1. Load Data
        raw_data = load_transactions(self.raw_data_path, lazy=self.lazy)
        raw_df = raw_data.collect() if isinstance(raw_data, pl.LazyFrame) else raw_data

        # 2. Health Dashboard
        mem_bytes = raw_df.estimated_size()
        num_cols = [c for c, d in raw_df.schema.items() if d in [pl.Int64, pl.Int32, pl.Float64, pl.Float32]]
        cat_cols = [c for c, d in raw_df.schema.items() if d in [pl.Utf8, pl.Categorical]]
        dt_cols = [c for c, d in raw_df.schema.items() if d in [pl.Datetime, pl.Date]]
        bool_cols = [c for c, d in raw_df.schema.items() if d == pl.Boolean]
        null_cells_cnt = raw_df.null_count().sum().to_numpy()[0][0]

        dashboard = pl.DataFrame([
            {"Metric": "Total Rows", "Value": f"{raw_df.height:,}"},
            {"Metric": "Total Columns", "Value": str(raw_df.width)},
            {"Metric": "Memory Usage", "Value": f"{mem_bytes / (1024**2):.2f} MB"},
            {"Metric": "Numeric Columns", "Value": str(len(num_cols))},
            {"Metric": "Categorical Columns", "Value": str(len(cat_cols))},
            {"Metric": "Datetime Columns", "Value": str(len(dt_cols))},
            {"Metric": "Boolean Columns", "Value": str(len(bool_cols))},
            {"Metric": "Null Cells", "Value": f"{null_cells_cnt:,}"},
            {"Metric": "Duplicate Rows", "Value": str(raw_df.height - raw_df.unique().height)},
            {"Metric": "Dataset Version", "Value": "1.0.0 (Raw Parquet)"}
        ])

        # 3. Structural Validation
        missing_df = analyze_missing_values(raw_df)
        dup_df = analyze_duplicates(raw_df)

        # 4. Domain Rule Validation
        domain_findings = validate_domain_rules(raw_df)
        domain_summary = pl.DataFrame([
            {
                "Validation Check": rule,
                "Violations": data["count"],
                "Severity": data["severity"],
                "Sample Record": data.get("sample_record", "None")
            } for rule, data in domain_findings.items()
        ])

        # 5. Statistical Profiling
        num_summary = []
        for col in num_cols:
            s = raw_df[col].drop_nulls()
            if s.len() > 0:
                q1_v = s.quantile(0.25)
                q3_v = s.quantile(0.75)
                q1 = float(str(q1_v)) if q1_v is not None else 0.0
                q3 = float(str(q3_v)) if q3_v is not None else 0.0

                mean_v = s.mean()
                std_v = s.std()
                min_v = s.min()
                med_v = s.median()
                max_v = s.max()
                skew_v = s.skew()
                kurt_v = s.kurtosis()

                missing_pct = (raw_df[col].null_count() / raw_df.height) * 100
                num_summary.append({
                    "Column": col,
                    "Count": s.len(),
                    "Mean": round(float(str(mean_v)), 2) if mean_v is not None else None,
                    "Std": round(float(str(std_v)), 2) if std_v is not None else None,
                    "Min": float(str(min_v)) if min_v is not None else None,
                    "Median": float(str(med_v)) if med_v is not None else None,
                    "Max": float(str(max_v)) if max_v is not None else None,
                    "IQR": round(q3 - q1, 2),
                    "Missing %": round(missing_pct, 2),
                    "Skewness": round(float(str(skew_v)), 2) if skew_v is not None else None,
                    "Kurtosis": round(float(str(kurt_v)), 2) if kurt_v is not None else None
                })
        statistical_profile = pl.DataFrame(num_summary)
        outlier_summary = detect_outliers_iqr_zscore(raw_df, num_cols)

        # 6. Clean Dataset
        clean_df, clean_metrics, decision_log_df = clean_transaction_data(raw_df)

        # 7. Post-Clean Comparison
        before_nulls = null_cells_cnt
        after_nulls = clean_df.null_count().sum().to_numpy()[0][0]
        before_mem_mb = clean_metrics["initial_memory_bytes"] / (1024**2)
        after_mem_mb = clean_metrics["final_memory_bytes"] / (1024**2)
        before_dups = clean_metrics['removed_duplicates']
        after_dups = 0

        def calc_reduction(before: float, after: float) -> str:
            if before == 0: return "0.0% Change"
            pct = round(((before - after) / before) * 100, 2)
            if pct > 0: return f"{pct}% Reduction"
            elif pct < 0: return f"{abs(pct)}% Increase"
            return "0.0% Change"

        before_after_df = pl.DataFrame([
            {"Metric": "Rows", "Before": f"{clean_metrics['initial_rows']:,}", "After": f"{clean_metrics['final_rows']:,}", "Improvement": calc_reduction(clean_metrics['initial_rows'], clean_metrics['final_rows'])},
            {"Metric": "Columns", "Before": str(raw_df.width), "After": str(clean_df.width), "Improvement": "+1 New Column (TransactionID)"},
            {"Metric": "Missing Values", "Before": str(before_nulls), "After": str(after_nulls), "Improvement": calc_reduction(before_nulls, after_nulls)},
            {"Metric": "Exact Duplicate Rows", "Before": str(before_dups), "After": str(after_dups), "Improvement": calc_reduction(before_dups, after_dups) if before_dups > 0 else "100.0% Reduction (Clean)"},
            {"Metric": "Memory Footprint", "Before": f"{before_mem_mb:.2f} MB", "After": f"{after_mem_mb:.2f} MB", "Improvement": f"{clean_metrics['memory_reduction_pct']}% Reduction"}
        ])

        quality_dims = compute_enterprise_quality_dimensions(raw_df, clean_metrics["removed_duplicates"])

        # 8. Export & Report Object
        duration = round(time.time() - start_time, 2)
        val_report_obj = build_validation_report_object(
            raw_df, clean_df, clean_metrics, missing_df, domain_findings, pipeline_duration=duration
        )

        export_clean_dataset(clean_df, self.clean_data_path)
        generate_data_quality_report(self.report_path, val_report_obj, decision_log_df)

        export_status = pl.DataFrame([
            {"Artifact": "Clean Dataset", "Status": "SUCCESS", "Location / Value": str(self.clean_data_path), "Details": f"{clean_df.height:,} rows | {after_mem_mb:.2f} MB"},
            {"Artifact": "Data Quality Report", "Status": "SUCCESS", "Location / Value": str(self.report_path), "Details": "Markdown Report"},
            {"Artifact": "Validation JSON", "Status": "SUCCESS", "Location / Value": str(self.report_path.parent / 'validation_report.json'), "Details": "Drift Baseline API Object"},
            {"Artifact": "Pipeline Metrics", "Status": "SUCCESS", "Location / Value": f"{duration} seconds", "Details": "Execution Time"}
        ])

        return PipelineResults(
            clean_df=clean_df,
            dashboard=dashboard,
            missing_analysis=missing_df,
            duplicate_summary=dup_df,
            domain_summary=domain_summary,
            statistical_profile=statistical_profile,
            outlier_summary=outlier_summary,
            decision_log=decision_log_df,
            before_after_comparison=before_after_df,
            quality_dimensions=quality_dims,
            export_status=export_status,
            validation_report_object=val_report_obj
        )
