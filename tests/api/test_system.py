"""
Test Suite for FastAPI System and Metadata Endpoints (/api/v1/model, /api/v1/features, /api/v1/version, /api/v1/info).
"""
try:
    from fraud_detection.api.app import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
except ImportError:
    import pytest
    pytestmark = pytest.mark.skip(reason="FastAPI app subpackage not available")
    client = None



def test_get_model_metadata():
    if client is None:
        return
    response = client.get("/api/v1/model")
    assert response.status_code == 200
    data = response.json()
    assert "LightGBM" in data["model_name"]
    assert data["algorithm"] == "LGBMClassifier"
    assert abs(data["threshold"] - 0.2556561085972851) < 1e-5


def test_get_feature_store_info():
    if client is None:
        return
    response = client.get("/api/v1/features")
    assert response.status_code == 200
    data = response.json()
    assert data["raw_feature_count"] >= 11
    assert data["processed_feature_count"] == 61


def test_get_system_version_and_info():
    if client is None:
        return
    response = client.get("/api/v1/version")
    assert response.status_code == 200
    data = response.json()
    assert data["package_version"] == "1.0.0"
    assert data["api_version"] == "1.0.0"

    info_resp = client.get("/api/v1/info")
    assert info_resp.status_code == 200
