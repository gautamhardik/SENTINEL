"""
Structured Logger with Console, Warehouse Log, ETL Log, and Error Log Handlers.
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Union

from src.warehouse.database import DOCS_DIR, WarehouseConnection


def get_warehouse_logger(name: str = "WarehouseETL") -> logging.Logger:
    """Configures multi-destination rotating log handlers for warehouse, etl, and errors."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

        # Console Handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        log_dir = DOCS_DIR.parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Rotating Warehouse Log
        wh_handler = RotatingFileHandler(log_dir / "warehouse.log", maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
        wh_handler.setFormatter(formatter)
        logger.addHandler(wh_handler)

        # Rotating ETL Log
        etl_handler = RotatingFileHandler(log_dir / "etl.log", maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
        etl_handler.setFormatter(formatter)
        logger.addHandler(etl_handler)

        # Rotating Error Log
        err_handler = RotatingFileHandler(log_dir / "error.log", maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
        err_handler.setLevel(logging.ERROR)
        err_handler.setFormatter(formatter)
        logger.addHandler(err_handler)

    return logger


class SQLRunner:
    """Executes external SQL script files and parameterized queries."""
    def __init__(self, db_conn: WarehouseConnection):
        self.db_conn = db_conn

    def execute_file(self, sql_file_path: Union[str, Path]) -> None:
        sql_file_path = Path(sql_file_path)
        if not sql_file_path.exists():
            raise FileNotFoundError(f"SQL script file not found at: {sql_file_path}")

        with open(sql_file_path, "r", encoding="utf-8") as f:
            sql_script = f.read()

        conn = self.db_conn.connect()
        statements = [stmt.strip() for stmt in sql_script.split(";") if stmt.strip()]

        if self.db_conn.engine_type == "postgresql":
            with conn.cursor() as cur:
                for stmt in statements:
                    cur.execute(stmt)
            conn.commit()
        else:
            for stmt in statements:
                conn.execute(stmt)

    def execute_query(self, query: str) -> Any:
        conn = self.db_conn.connect()
        if self.db_conn.engine_type == "postgresql":
            with conn.cursor() as cur:
                cur.execute(query)
                if cur.description:
                    return cur.fetchall()
            conn.commit()
            return None
        else:
            res = conn.execute(query)
            if res.description:
                return res.fetchall()
            return None
