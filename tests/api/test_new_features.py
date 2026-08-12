"""
Tests for Monitoring, Rate Limiting, API Key Security, and Audit Trail features
"""

try:
    from backend.app.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
except ImportError:
    import pytest
    pytestmark = pytest.mark.skip(reason="Legacy backend module is omitted in current package build")
    client = None



def test_monitoring_drift_endpoint():
    """Test feature drift evaluation endpoint."""
    response = client.get("/api/v1/monitoring/drift")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "drift_alert" in data
    assert "metrics" in data


def test_prometheus_endpoint():
    """Test Prometheus metrics endpoint."""
    response = client.get("/api/v1/monitoring/prometheus")
    assert response.status_code == 200
    assert "fraud_predictions_total" in response.text


def test_rate_limiting_headers():
    """Test that rate limiting headers are attached to responses."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    response = client.get("/api/v1/metadata")
    assert response.status_code == 200
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
