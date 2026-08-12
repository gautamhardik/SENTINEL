"""
Analytics SQL Script Executor & Query Engine.
"""
import time
from pathlib import Path
from typing import Any, Dict, List, Union

import polars as pl

from src.warehouse.database import WarehouseConnection
from src.warehouse.logger import get_warehouse_logger


class AnalyticsExecutor:
    """Executes SQL analytics scripts and returns structured Polars DataFrames."""
    def __init__(self, db_conn: WarehouseConnection):
        self.db_conn = db_conn
        self.logger = get_warehouse_logger("AnalyticsExecutor")

    def execute_script(self, script_path: Union[str, Path]) -> List[Dict[str, Any]]:
        script_path = Path(script_path)
        if not script_path.exists():
            raise FileNotFoundError(f"Analytics SQL script not found at: {script_path}")

        with open(script_path, "r", encoding="utf-8") as f:
            sql_content = f.read()

        try:
            conn = self.db_conn.connect()
            is_pg = self.db_conn.engine_type == "postgresql"

            # Split by semicolon while preserving clean multi-line SQL statements
            raw_chunks = sql_content.split(";")
            statements = []
            for chunk in raw_chunks:
                lines = [l for l in chunk.splitlines() if l.strip() and not l.strip().startswith("--")]
                stmt = " ".join(lines).strip()
                if stmt:
                    statements.append(stmt)

            results = []
            for idx, stmt in enumerate(statements):
                start_t = time.time()
                try:
                    if is_pg:
                        with conn.cursor() as cur:
                            cur.execute(stmt)
                            if cur.description:
                                cols = [desc[0] for desc in cur.description]
                                rows = cur.fetchall()
                                df = pl.DataFrame(rows, schema=cols, orient="row")
                            else:
                                df = pl.DataFrame({"status": ["SUCCESS"]})
                    else:
                        res = conn.execute(stmt)
                        if res.description:
                            cols = [desc[0] for desc in res.description]
                            rows = res.fetchall()
                            df = pl.DataFrame(rows, schema=cols, orient="row")
                        else:
                            df = pl.DataFrame({"status": ["SUCCESS"]})

                    duration = round(time.time() - start_t, 3)
                    results.append({
                        "statement_index": idx + 1,
                        "dataframe": df,
                        "execution_time_sec": duration
                    })
                except Exception as e:
                    self.logger.error(f"Error executing statement {idx + 1}: {e}")
                    results.append({
                        "statement_index": idx + 1,
                        "dataframe": pl.DataFrame({"error": [str(e)]}),
                        "execution_time_sec": 0.0
                    })

            return results
        finally:
            self.db_conn.close()

    def query(self, sql_query: str) -> pl.DataFrame:
        conn = self.db_conn.connect()
        is_pg = self.db_conn.engine_type == "postgresql"
        if is_pg:
            with conn.cursor() as cur:
                cur.execute(sql_query)
                if cur.description:
                    cols = [desc[0] for desc in cur.description]
                    return pl.DataFrame(cur.fetchall(), schema=cols, orient="row")
            return pl.DataFrame({"status": ["SUCCESS"]})
        else:
            res = conn.execute(sql_query)
            if res.description:
                cols = [desc[0] for desc in res.description]
                return pl.DataFrame(res.fetchall(), schema=cols, orient="row")
            return pl.DataFrame({"status": ["SUCCESS"]})
