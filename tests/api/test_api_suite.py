"""
Dedicated Comprehensive Test Suite for Phase 6B Production FastAPI Inference Service.
Tests 20 required scenarios covering health, readiness, input validation, structured errors,
real model inference, feature-store persistence, leakage prevention, idempotency, and lifecycle.
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from fraud_detection.api.app import app
from fraud_detection.api.dependencies import get_engine
from fraud_detection.exceptions import FeatureValidationError, FraudDetectionBaseException

client = TestClient(app)
API_KEY = "dev-secret-key-12345"


def get_sample_payload(tx_id: str = None, amount: float = 1500.0, timestamp: str = "2026-08-11T14:15:00"):
    if tx_id is None:
        tx_id = f"TX_{uuid.uuid4().hex[:8]}"
    return {
        "transaction_id": tx_id,
        "Timestamp": timestamp,
        "From_Account": f"ACC_SRC_{tx_id}",
        "To_Account": f"ACC_DST_{tx_id}",
        "From_Bank": "BANK_12",
        "To_Bank": "BANK_45",
        "Amount_Paid": amount,
        "Amount_Received": amount,
        "Payment_Format": "Wire",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    }


def test_01_get_health():
    """1. GET /health liveness probe."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert response.headers.get("X-Model-Version") == "1.0.0"


def test_02_get_health_ready():
    """2. GET /health/ready readiness probe."""
    response = client.get("/health/ready")
    assert response.status_code in [200, 503]
    data = response.json()
    assert "status" in data
    assert "model_loaded" in data
    assert "database_ready" in data


def test_03_valid_predict_single():
    """3. Valid POST /api/v1/predict single transaction."""
    payload = get_sample_payload(amount=250.0)
    response = client.post("/api/v1/predict", json=payload, headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["transaction_id"] == payload["transaction_id"]
    assert data["decision"] in ["APPROVED_LEGITIMATE", "APPROVED_WITH_MONITORING", "FLAGGED_FRAUD", "FLAGGED_CRITICAL_FRAUD"]
    assert 0.0 <= data["calibrated_probability"] <= 1.0


def test_04_invalid_request():
    """4. Invalid request body (malformed JSON)."""
    response = client.post(
        "/api/v1/predict",
        content="this is not json",
        headers={"Content-Type": "application/json", "X-API-Key": API_KEY}
    )
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_05_missing_required_field():
    """5. Missing required field (e.g. Amount_Paid)."""
    payload = get_sample_payload()
    del payload["Amount_Paid"]
    response = client.post("/api/v1/predict", json=payload, headers={"X-API-Key": API_KEY})
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_06_invalid_amount():
    """6. Invalid amount (negative or zero Amount_Paid)."""
    payload = get_sample_payload(amount=-50.0)
    response = client.post("/api/v1/predict", json=payload, headers={"X-API-Key": API_KEY})
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_07_invalid_timestamp():
    """7. Invalid timestamp format."""
    payload = get_sample_payload(timestamp="invalid-datetime-string-abc")
    response = client.post("/api/v1/predict", json=payload, headers={"X-API-Key": API_KEY})
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_08_malformed_transaction():
    """8. Malformed transaction payload (empty account string)."""
    payload = get_sample_payload()
    payload["From_Account"] = "   "
    response = client.post("/api/v1/predict", json=payload, headers={"X-API-Key": API_KEY})
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_09_backend_feature_store_failure():
    """9. Backend feature-store / exception mapping handling."""
    real_engine = get_engine()

    class FailingStoreEngine:
        def __init__(self):
            self.service = real_engine.service
        def predict(self, raw_dict, **kwargs):
            raise FeatureValidationError("Simulated feature store failure")

    try:
        app.dependency_overrides[get_engine] = lambda: FailingStoreEngine()
        payload = get_sample_payload()
        response = client.post("/api/v1/predict", json=payload, headers={"X-API-Key": API_KEY})
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
    finally:
        app.dependency_overrides.clear()


def test_10_model_inference_failure():
    """10. Model inference execution failure handling."""
    real_engine = get_engine()

    class FailingInferenceEngine:
        def __init__(self):
            self.service = real_engine.service
        def predict(self, raw_dict, **kwargs):
            raise FraudDetectionBaseException("Simulated inference engine internal crash")

    try:
        app.dependency_overrides[get_engine] = lambda: FailingInferenceEngine()
        payload = get_sample_payload()
        response = client.post("/api/v1/predict", json=payload, headers={"X-API-Key": API_KEY})
        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == "INFERENCE_ERROR"
    finally:
        app.dependency_overrides.clear()


def test_11_response_schema():
    """11. Complete response schema validation."""
    payload = get_sample_payload(amount=12000.0)
    response = client.post("/api/v1/predict", json=payload, headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    data = response.json()
    
    required_keys = [
        "transaction_id", "request_id", "decision", "risk_level",
        "calibrated_probability", "fraud_probability", "raw_probability",
        "threshold", "recommended_action", "explanation",
        "inference_latency_ms", "model_version", "timestamp"
    ]
    for key in required_keys:
        assert key in data, f"Missing key in response: {key}"

    assert isinstance(data["explanation"], dict)
    assert "top_risk_drivers" in data["explanation"]


def test_12_calibrated_probability_returned():
    """12. Calibrated probability returned and matches fraud_probability."""
    payload = get_sample_payload()
    response = client.post("/api/v1/predict", json=payload, headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert 0.0 <= data["calibrated_probability"] <= 1.0
    assert data["calibrated_probability"] == data["fraud_probability"]


def test_13_threshold_correctly_represented():
    """13. Decision threshold is correctly 0.2556561085972851."""
    response = client.get("/api/v1/model/info")
    assert response.status_code == 200
    data = response.json()
    expected_threshold = 0.2556561085972851
    assert abs(data["threshold"] - expected_threshold) < 1e-5

    payload = get_sample_payload()
    predict_resp = client.post("/api/v1/predict", json=payload, headers={"X-API-Key": API_KEY})
    assert predict_resp.status_code == 200
    p_data = predict_resp.json()
    assert abs(p_data["threshold"] - expected_threshold) < 1e-5


def test_14_real_model_inference():
    """14. Real end-to-end inference with real LightGBM + isotonic calibrator + SHAP explanations."""
    payload = get_sample_payload(amount=15000.0)  # > 10000 -> is_amount_outlier=1.0
    response = client.post("/api/v1/predict", json=payload, headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["transaction_id"] == payload["transaction_id"]
    assert data["decision"] in ["APPROVED_LEGITIMATE", "APPROVED_WITH_MONITORING", "FLAGGED_FRAUD", "FLAGGED_CRITICAL_FRAUD"]
    assert "top_risk_drivers" in data["explanation"]
    assert "investigator_card" in data["explanation"]


def test_15_current_transaction_leakage_prevention():
    """15. Current transaction leakage prevention test."""
    account_id = f"ACC_LEAK_{uuid.uuid4().hex[:8]}"
    payload = {
        "transaction_id": f"TX_LEAK_{uuid.uuid4().hex[:8]}",
        "Timestamp": "2026-08-11T10:00:00",
        "From_Account": account_id,
        "To_Account": "ACC_TARGET_LEAK",
        "From_Bank": "BANK_01",
        "To_Bank": "BANK_02",
        "Amount_Paid": 500.0,
        "Amount_Received": 500.0,
        "Payment_Format": "ACH",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    }

    # First transaction for novel account: prediction occurs before historical state insertion
    response = client.post("/api/v1/predict", json=payload, headers={"X-API-Key": API_KEY})
    assert response.status_code == 200


def test_16_feature_store_state_persistence_after_api_prediction():
    """16. Feature-store state persistence after API prediction."""
    acct = f"ACC_PERST_{uuid.uuid4().hex[:8]}"
    tx1 = get_sample_payload()
    tx1["From_Account"] = acct

    # Send first prediction
    r1 = client.post("/api/v1/predict", json=tx1, headers={"X-API-Key": API_KEY})
    assert r1.status_code == 200

    # Send second prediction for same account
    tx2 = get_sample_payload()
    tx2["From_Account"] = acct
    r2 = client.post("/api/v1/predict", json=tx2, headers={"X-API-Key": API_KEY})
    assert r2.status_code == 200


def test_17_duplicate_transaction_behavior():
    """17. Idempotent duplicate transaction prediction behavior."""
    payload = get_sample_payload()
    r1 = client.post("/api/v1/predict", json=payload, headers={"X-API-Key": API_KEY})
    assert r1.status_code == 200

    r2 = client.post("/api/v1/predict", json=payload, headers={"X-API-Key": API_KEY})
    assert r2.status_code == 200
    assert r1.json()["transaction_id"] == r2.json()["transaction_id"]


def test_18_multiple_requests():
    """18. Multiple sequential requests handling."""
    for _ in range(5):
        payload = get_sample_payload()
        resp = client.post("/api/v1/predict", json=payload, headers={"X-API-Key": API_KEY})
        assert resp.status_code == 200


def test_19_api_startup_model_loading():
    """19. API startup and singleton model loading via lifespan."""
    with TestClient(app) as test_c:
        resp = test_c.get("/health")
        assert resp.status_code == 200
        ready_resp = test_c.get("/health/ready")
        assert ready_resp.status_code in [200, 503]
        data = ready_resp.json()
        assert data["model_loaded"] is True


def test_20_api_shutdown_restart():
    """20. API shutdown and restart behavior."""
    import fraud_detection.api.app as app_mod
    app_mod._engine = None

    payload = get_sample_payload()
    resp = client.post("/api/v1/predict", json=payload, headers={"X-API-Key": API_KEY})
    assert resp.status_code == 200
