"""
Test Suite for FastAPI Lifespan Startup Warmup, Security, and Exception Handler mapping.
"""
try:
    from fraud_detection.api.app import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
except ImportError:
    import pytest
    pytestmark = pytest.mark.skip(reason="FastAPI app subpackage not available")
    client = None

API_KEY = "dev-secret-key-12345"


def test_lifespan_and_startup():
    with TestClient(app) as test_c:
        resp = test_c.get("/health")
        assert resp.status_code == 200


def test_custom_exception_handler_mapping():
    if client is None:
        return
    from fraud_detection.exceptions import ArtifactNotFoundError, ConfigurationError, FeatureValidationError
    from fraud_detection.api.dependencies import get_engine

    real_engine = get_engine()

    class MockEngineError:
        def __init__(self):
            self.service = real_engine.service
        def predict(self, *args, **kwargs):
            raise FeatureValidationError("Mock feature error")

    class MockRegistryError:
        def __init__(self):
            self.service = real_engine.service
        def predict(self, *args, **kwargs):
            raise ArtifactNotFoundError("Mock registry error")

    class MockConfigError:
        def __init__(self):
            self.service = real_engine.service
        def predict(self, *args, **kwargs):
            raise ConfigurationError("Mock config error")

    class MockGenericError:
        def __init__(self):
            self.service = real_engine.service
        def predict(self, *args, **kwargs):
            raise RuntimeError("Mock unhandled error")

    valid_payload = {
        "transaction_id": "T1",
        "Timestamp": "2026-08-11 12:00:00",
        "From_Account": "A1",
        "To_Account": "A2",
        "From_Bank": "10",
        "To_Bank": "20",
        "Amount_Paid": 10.0,
        "Amount_Received": 10.0,
        "Payment_Format": "ACH",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    }

    try:
        app.dependency_overrides[get_engine] = lambda: MockEngineError()
        resp = client.post("/api/v1/predict", json=valid_payload, headers={"X-API-Key": API_KEY})
        assert resp.status_code == 400
        assert resp.json()["error"]["title"] == "Feature Validation Error"

        app.dependency_overrides[get_engine] = lambda: MockRegistryError()
        resp = client.post("/api/v1/predict", json=valid_payload, headers={"X-API-Key": API_KEY})
        assert resp.status_code == 503
        assert resp.json()["error"]["title"] == "Model Registry Service Unavailable"

        app.dependency_overrides[get_engine] = lambda: MockConfigError()
        resp = client.post("/api/v1/predict", json=valid_payload, headers={"X-API-Key": API_KEY})
        assert resp.status_code == 500
        assert resp.json()["error"]["title"] == "System Configuration Error"

        app.dependency_overrides[get_engine] = lambda: MockGenericError()
        with TestClient(app, raise_server_exceptions=False) as lenient_client:
            resp = lenient_client.post("/api/v1/predict", json=valid_payload, headers={"X-API-Key": API_KEY})
        assert resp.status_code == 500
    finally:
        app.dependency_overrides.clear()
