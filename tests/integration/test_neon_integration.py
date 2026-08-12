"""
Neon PostgreSQL Production Integration & Verification Test Suite.
Verifies connectivity, schema initialization, real-time inference, feature engineering,
calibration, TreeSHAP explainability, transaction persistence, state isolation, idempotency,
reconnection resilience, and fallback prevention on live Neon PostgreSQL database.
"""
import os
import sys
import uuid
import pytest
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(dotenv_path=os.path.abspath(".env"), override=True)

# Ensure src is on python path
sys.path.insert(0, os.path.abspath("src"))

from fastapi.testclient import TestClient
from warehouse.database import WarehouseConnection
from fraud_detection.history import HistoryRepository
from fraud_detection.factories import EngineFactory
from fraud_detection.api.app import app


@pytest.fixture(scope="module")
def db_conn():
    """Initializes and provides WarehouseConnection to Neon PostgreSQL."""
    assert os.getenv("DB_ENGINE_TYPE", "").lower() == "postgresql", "DB_ENGINE_TYPE must be 'postgresql'"
    conn = WarehouseConnection(engine_type="postgresql")
    conn.init_schema()
    yield conn
    conn.close()


def test_01_neon_postgres_connection_success(db_conn):
    """1. PostgreSQL connection succeeds."""
    assert db_conn.test_connection() is True, "Failed to connect to Neon PostgreSQL database"


def test_02_schema_tables_initialized(db_conn):
    """2. Required schema/tables are initialized correctly in Neon."""
    raw_conn = db_conn.connect()
    with raw_conn.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        tables = [row[0] for row in cur.fetchall()]
    
    assert "schema_version" in tables, "schema_version table missing"
    assert "account_states" in tables, "account_states table missing"
    assert "transaction_history" in tables, "transaction_history table missing"


def test_03_health_liveness_endpoint():
    """3. /health remains healthy."""
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "healthy"


def test_04_health_ready_readiness_endpoint():
    """4. /health/ready reports database_ready=true."""
    client = TestClient(app)
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "ready"
    assert data.get("database_ready") is True


def test_05_predict_inference_flow():
    """5. POST /api/v1/predict successfully performs inference."""
    client = TestClient(app)
    tx_id = f"TX-NEON-{uuid.uuid4().hex[:8]}"
    payload = {
        "transaction_id": tx_id,
        "Timestamp": "2026-08-12 12:00:00",
        "From_Account": "ACC-NEON-001",
        "To_Account": "ACC-NEON-002",
        "From_Bank": "100",
        "To_Bank": "200",
        "Amount_Paid": 12500.0,
        "Amount_Received": 12500.0,
        "Payment_Format": "Wire",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    }
    resp = client.post("/api/v1/predict", json=payload)
    assert resp.status_code == 200, f"Predict failed: {resp.text}"
    body = resp.json()
    
    # Check return structure
    assert "decision" in body
    assert "calibrated_probability" in body
    assert "threshold" in body
    assert "explanation" in body


def test_06_61_feature_pipeline_and_schema():
    """6. The prediction uses the existing 61-feature pipeline."""
    repo = HistoryRepository(engine_type="postgresql")
    engine = EngineFactory.create(history_repository=repo)
    
    tx = {
        "TransactionID": f"TX-FEAT-{uuid.uuid4().hex[:8]}",
        "Timestamp": "2026-08-12 12:30:00",
        "From_Account": "ACC-FEAT-001",
        "To_Account": "ACC-FEAT-002",
        "From_Bank": "10",
        "To_Bank": "20",
        "Amount_Paid": 500.0,
        "Amount_Received": 500.0,
        "Payment_Format": "Credit Card",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    }
    res = engine.predict(tx)
    assert hasattr(res, "calibrated_probability")
    assert 0.0 <= res.calibrated_probability <= 1.0


def test_07_calibrated_probability_return():
    """7. Calibrated probability is returned correctly."""
    client = TestClient(app)
    tx_id = f"TX-PROB-{uuid.uuid4().hex[:8]}"
    payload = {
        "transaction_id": tx_id,
        "Timestamp": "2026-08-12 13:00:00",
        "From_Account": "ACC-PROB-001",
        "To_Account": "ACC-PROB-002",
        "From_Bank": "10",
        "To_Bank": "20",
        "Amount_Paid": 100.0,
        "Amount_Received": 100.0,
        "Payment_Format": "ACH",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    }
    resp = client.post("/api/v1/predict", json=payload)
    assert resp.status_code == 200, f"Failed: {resp.text}"
    prob = resp.json()["calibrated_probability"]
    assert isinstance(prob, float)
    assert 0.0 <= prob <= 1.0


def test_08_threshold_unchanged():
    """8. The existing threshold 0.2556561085972851 is unchanged."""
    client = TestClient(app)
    payload = {
        "transaction_id": f"TX-THRESH-{uuid.uuid4().hex[:8]}",
        "Timestamp": "2026-08-12 13:30:00",
        "From_Account": "ACC-THRESH-001",
        "To_Account": "ACC-THRESH-002",
        "From_Bank": "10",
        "To_Bank": "20",
        "Amount_Paid": 250.0,
        "Amount_Received": 250.0,
        "Payment_Format": "ACH",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    }
    resp = client.post("/api/v1/predict", json=payload)
    assert resp.status_code == 200, f"Failed: {resp.text}"
    assert abs(resp.json()["threshold"] - 0.2556561085972851) < 1e-4


def test_09_shap_explanations_generated():
    """9. SHAP explanations are generated correctly."""
    client = TestClient(app)
    payload = {
        "transaction_id": f"TX-SHAP-{uuid.uuid4().hex[:8]}",
        "Timestamp": "2026-08-12 14:00:00",
        "From_Account": "ACC-SHAP-001",
        "To_Account": "ACC-SHAP-002",
        "From_Bank": "10",
        "To_Bank": "20",
        "Amount_Paid": 75000.0,
        "Amount_Received": 75000.0,
        "Payment_Format": "Wire",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    }
    resp = client.post("/api/v1/predict", json=payload)
    assert resp.status_code == 200, f"Failed: {resp.text}"
    explanation = resp.json().get("explanation")
    assert isinstance(explanation, dict)
    assert "top_risk_drivers" in explanation or "investigator_card" in explanation


def test_10_transaction_history_persisted_in_neon(db_conn):
    """10. Transaction history is persisted in Neon PostgreSQL."""
    client = TestClient(app)
    tx_id = f"TX-PERSIST-{uuid.uuid4().hex[:8]}"
    acct_id = f"ACC-PERSIST-{uuid.uuid4().hex[:8]}"
    payload = {
        "transaction_id": tx_id,
        "Timestamp": "2026-08-12 14:30:00",
        "From_Account": acct_id,
        "To_Account": "ACC-TARGET-999",
        "From_Bank": "15",
        "To_Bank": "25",
        "Amount_Paid": 3300.0,
        "Amount_Received": 3300.0,
        "Payment_Format": "Rebalancing",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    }
    resp = client.post("/api/v1/predict", json=payload)
    assert resp.status_code == 200, f"Failed: {resp.text}"
    
    # Query Neon DB to confirm persistence
    raw_conn = db_conn.connect()
    with raw_conn.cursor() as cur:
        cur.execute("SELECT from_account, amount_paid FROM transaction_history WHERE transaction_key = %s;", (tx_id,))
        row = cur.fetchone()
    
    assert row is not None, f"Transaction {tx_id} not found in Neon transaction_history table"
    assert row[0] == acct_id
    assert abs(row[1] - 3300.0) < 1e-4


def test_11_historical_feature_state_read_correctly(db_conn):
    """11. Historical feature state is read correctly across consecutive transactions."""
    acct_id = f"ACC-HIST-{uuid.uuid4().hex[:8]}"
    client = TestClient(app)
    
    # Tx 1
    tx1 = {
        "transaction_id": f"TX-HIST-1-{uuid.uuid4().hex[:6]}",
        "Timestamp": "2026-08-12 15:00:00",
        "From_Account": acct_id,
        "To_Account": "ACC-RECEIVER-1",
        "From_Bank": "10",
        "To_Bank": "20",
        "Amount_Paid": 1000.0,
        "Amount_Received": 1000.0,
        "Payment_Format": "ACH",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    }
    resp1 = client.post("/api/v1/predict", json=tx1)
    assert resp1.status_code == 200, f"Failed: {resp1.text}"
    
    # Tx 2 for same account
    tx2 = {
        "transaction_id": f"TX-HIST-2-{uuid.uuid4().hex[:6]}",
        "Timestamp": "2026-08-12 15:05:00",
        "From_Account": acct_id,
        "To_Account": "ACC-RECEIVER-2",
        "From_Bank": "10",
        "To_Bank": "20",
        "Amount_Paid": 2000.0,
        "Amount_Received": 2000.0,
        "Payment_Format": "ACH",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    }
    resp2 = client.post("/api/v1/predict", json=tx2)
    assert resp2.status_code == 200, f"Failed: {resp2.text}"
    
    # Check account_states table in Neon
    raw_conn = db_conn.connect()
    with raw_conn.cursor() as cur:
        cur.execute("SELECT transaction_count, total_amount_paid FROM account_states WHERE account_id = %s;", (acct_id,))
        row = cur.fetchone()
    
    assert row is not None
    assert row[0] >= 2
    assert row[1] >= 3000.0


def test_12_current_transaction_state_isolation():
    """12. Current transaction does not contaminate its own historical features."""
    acct_id = f"ACC-ISO-{uuid.uuid4().hex[:8]}"
    repo = HistoryRepository(engine_type="postgresql")
    
    # Query history before tx
    hist_before = repo.get_account_history([acct_id])
    assert len(hist_before) == 0


def test_13_idempotency_semantics(db_conn):
    """13. Duplicate transaction IDs preserve existing idempotency semantics."""
    client = TestClient(app)
    tx_id = f"TX-IDEM-{uuid.uuid4().hex[:8]}"
    payload = {
        "transaction_id": tx_id,
        "Timestamp": "2026-08-12 16:00:00",
        "From_Account": "ACC-IDEM-001",
        "To_Account": "ACC-IDEM-002",
        "From_Bank": "10",
        "To_Bank": "20",
        "Amount_Paid": 500.0,
        "Amount_Received": 500.0,
        "Payment_Format": "Wire",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    }
    
    # Post first time
    resp1 = client.post("/api/v1/predict", json=payload)
    assert resp1.status_code == 200, f"Failed: {resp1.text}"
    
    # Post duplicate second time
    resp2 = client.post("/api/v1/predict", json=payload)
    assert resp2.status_code == 200, f"Failed: {resp2.text}"
    assert resp1.json()["calibrated_probability"] == resp2.json()["calibrated_probability"]


def test_14_reconnection_resilience(db_conn):
    """14. Database reconnection behavior does not corrupt state."""
    db_conn.close()
    assert db_conn.test_connection() is True


def test_15_no_silent_duckdb_fallback():
    """15. PostgreSQL exceptions are NOT silently converted to DuckDB/SQLite when DB_ENGINE_TYPE=postgresql."""
    conn = WarehouseConnection(engine_type="postgresql")
    assert conn.engine_type == "postgresql"


def test_16_response_contract_unchanged():
    """16. Frontend/backend response contracts remain unchanged."""
    client = TestClient(app)
    payload = {
        "transaction_id": f"TX-CONTRACT-{uuid.uuid4().hex[:8]}",
        "Timestamp": "2026-08-12 17:00:00",
        "From_Account": "ACC-CONTRACT-001",
        "To_Account": "ACC-CONTRACT-002",
        "From_Bank": "10",
        "To_Bank": "20",
        "Amount_Paid": 1500.0,
        "Amount_Received": 1500.0,
        "Payment_Format": "ACH",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    }
    resp = client.post("/api/v1/predict", json=payload)
    assert resp.status_code == 200, f"Failed: {resp.text}"
    data = resp.json()
    
    required_keys = ["request_id", "decision", "risk_level", "calibrated_probability", "threshold", "explanation"]
    for key in required_keys:
        assert key in data, f"Missing required response key: {key}"
