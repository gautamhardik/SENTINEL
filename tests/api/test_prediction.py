"""
Test Suite for FastAPI Prediction Endpoints (/api/v1/predict and /api/v1/predict/batch).
"""
import pytest
try:
    from fraud_detection.api.app import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
except ImportError:
    import pytest
    pytestmark = pytest.mark.skip(reason="FastAPI app subpackage not available")
    client = None

API_KEY = "dev-secret-key-12345"


@pytest.fixture(scope="module")
def valid_payload():
    return {
        "transaction_id": "TX_TEST_001",
        "Timestamp": "2026-08-11 12:00:00",
        "From_Account": "acct_api_1",
        "To_Account": "acct_api_2",
        "From_Bank": "10",
        "To_Bank": "20",
        "Amount_Paid": 500.0,
        "Amount_Received": 500.0,
        "Payment_Format": "ACH",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    }


def test_predict_single_success(valid_payload):
    if client is None:
        return
    response = client.post(
        "/api/v1/predict",
        json=valid_payload,
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 200
    data = response.json()
    assert "request_id" in data
    assert data["decision"] in ["APPROVED_LEGITIMATE", "APPROVED_WITH_MONITORING", "FLAGGED_FRAUD", "FLAGGED_CRITICAL_FRAUD"]
    assert 0.0 <= data["calibrated_probability"] <= 1.0
    assert data["model_version"] == "v1.0.0"


def test_predict_single_missing_column(valid_payload):
    if client is None:
        return
    invalid_payload = dict(valid_payload)
    del invalid_payload["Amount_Paid"]

    response = client.post(
        "/api/v1/predict",
        json=invalid_payload,
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 422


def test_predict_batch_success(valid_payload):
    if client is None:
        return
    batch_payload = {
        "transactions": [valid_payload, valid_payload],
        "include_explanations": False
    }
    response = client.post(
        "/api/v1/predict/batch",
        json=batch_payload,
        headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["processed"] == 2
    assert data["successful"] == 2
    assert len(data["predictions"]) == 2
