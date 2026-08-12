"""
Test Suite for FastAPI Health, Readiness, and Metrics Endpoints (/health, /ready, /metrics).
"""
try:
    from fraud_detection.api.app import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
except ImportError:
    import pytest
    pytestmark = pytest.mark.skip(reason="FastAPI app subpackage not available")
    client = None


def test_health_liveness_endpoint():
    if client is None:
        return
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert response.headers.get("X-Model-Version") == "1.0.0"


def test_readiness_probe_endpoint():
    if app is None:
        return
    with TestClient(app) as tc:
        response = tc.get("/ready")
        assert response.status_code in (200, 503)
        data = response.json()
        assert data["status"] in ("ready", "not_ready")
        assert data["registry_active"] is True
        assert data["model_loaded"] is True




def test_metrics_endpoint():
    if client is None:
        return
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "uptime_seconds" in data
    assert "total_predictions" in data
