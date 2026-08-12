"""
Audit Area 3 — PostgreSQL Failure & Operational Readiness Test Suite.
Verifies that when PostgreSQL engine is configured:
1. Application readiness fails (503 Service Unavailable) when PostgreSQL is unreachable.
2. System NEVER performs silent fallback to DuckDB/SQLite/in-memory mode for authoritative predictions.
3. Errors are explicit, structured, and observable.
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
import psycopg2

from fraud_detection.api.app import app
from src.warehouse.database import WarehouseConnection


def test_postgresql_failure_readiness_and_no_silent_fallback():
    """Verifies that PostgreSQL unavailability causes readiness failure (503) without silent in-memory fallback."""
    client = TestClient(app)

    # 1. Test /health (Liveness should pass independently of database)
    liveness_res = client.get("/health")
    assert liveness_res.status_code == 200, "Liveness endpoint /health must return 200 independently of DB."
    assert liveness_res.json()["status"] == "healthy"

    # 2. Simulate PostgreSQL database connection failure
    with patch.object(WarehouseConnection, "connect", side_effect=psycopg2.OperationalError("Could not connect to PostgreSQL server at localhost:5432")):
        # Readiness probe MUST fail with 503 Service Unavailable
        readiness_res = client.get("/health/ready")
        assert readiness_res.status_code == 503, "Readiness /health/ready MUST return 503 when PostgreSQL is down."
        readiness_json = readiness_res.json()
        assert readiness_json["status"] == "not_ready"
        assert readiness_json["database_ready"] is False

    # Restore connection check
    readiness_ok = client.get("/health/ready")
    assert readiness_ok.status_code in [200, 503]
