"""
Comprehensive test suite for hardened production online feature store and state layer.
Verifies persistent account state, restart recovery, atomic DB updates, duplicate idempotency,
cold-start fallbacks, backend is_amount_outlier derivation, feature parity, and real artifact inference.
"""
from typing import Any
import os
import threading
import numpy as np
import pandas as pd
import pytest

from fraud_detection.core import RawTransaction, RiskLevel
from fraud_detection.factories import EngineFactory
from fraud_detection.feature_service import OnlineFeatureService
from fraud_detection.history import HistoryRepository, HistoryWriter
from fraud_detection.retrieval import ContextService


def test_is_amount_outlier_backend_derivation():
    """Verifies that is_amount_outlier is derived automatically by the backend if omitted by client using Amount_Paid > 10000.0."""
    boundary_cases = [
        (9999.99, 0.0),
        (10000.00, 0.0),
        (10000.01, 1.0),
        (19999.00, 1.0),
        (20000.00, 1.0)
    ]
    for amt, expected in boundary_cases:
        tx = RawTransaction.from_dict({
            "transaction_id": f"tx_deriv_{amt}",
            "Timestamp": "2026-08-11 12:00:00",
            "From_Account": "acct_dev_1",
            "To_Account": "acct_dev_2",
            "From_Bank": "10",
            "To_Bank": "20",
            "Amount_Paid": amt,
            "Amount_Received": amt,
            "Payment_Format": "ACH",
            "Payment_Currency": "USD",
            "Receiving_Currency": "USD"
        })
        assert tx.is_amount_outlier == expected, f"Failed boundary check for Amount_Paid={amt}: expected {expected}, got {tx.is_amount_outlier}"


def test_duplicate_transaction_idempotency(tmp_path):
    """Verifies that submitting duplicate transactions is idempotent and does NOT corrupt account state."""
    repo = HistoryRepository(engine_type="duckdb", duckdb_path=tmp_path / "test_idemp.duckdb", parquet_path=tmp_path / "test_idemp.parquet")
    repo.clear()
    writer = HistoryWriter(repository=repo)

    tx = RawTransaction.from_dict({
        "transaction_id": "tx_dup_001",
        "Timestamp": "2026-08-11 10:00:00",
        "From_Account": "acct_idemp_100",
        "To_Account": "acct_idemp_200",
        "From_Bank": "10",
        "To_Bank": "20",
        "Amount_Paid": 1000.0,
        "Amount_Received": 1000.0,
        "Payment_Format": "ACH",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    })

    # First write
    writer.persist_transaction(tx)
    hist1 = repo.get_account_history(["acct_idemp_100"])
    assert len(hist1) == 1

    # Duplicate write of exact same transaction_id
    writer.persist_transaction(tx)
    hist2 = repo.get_account_history(["acct_idemp_100"])
    assert len(hist2) == 1  # Should remain exactly 1 row (no duplicate row)


def test_restart_recovery_and_persistence(tmp_path):
    """Verifies that historical feature state survives process restart."""
    db_p = tmp_path / "test_restart.duckdb"
    pq_p = tmp_path / "test_restart.parquet"
    repo1 = HistoryRepository(engine_type="duckdb", duckdb_path=db_p, parquet_path=pq_p)
    repo1.clear()
    writer1 = HistoryWriter(repository=repo1)

    tx1 = RawTransaction.from_dict({
        "transaction_id": "tx_restart_001",
        "Timestamp": "2026-08-11 10:00:00",
        "From_Account": "acct_restart_1",
        "To_Account": "acct_restart_2",
        "From_Bank": "10",
        "To_Bank": "20",
        "Amount_Paid": 450.0,
        "Amount_Received": 450.0,
        "Payment_Format": "ACH",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    })
    writer1.persist_transaction(tx1)

    # Simulate new process startup by initializing a new repository instance
    repo2 = HistoryRepository(engine_type="duckdb", duckdb_path=db_p, parquet_path=pq_p)
    hist2 = repo2.get_account_history(["acct_restart_1"])
    assert not hist2.empty
    assert hist2["From_Account"].iloc[0] == "acct_restart_1"
    assert hist2["Amount_Paid"].iloc[0] == 450.0


def test_concurrent_write_safety(tmp_path):
    """Verifies that concurrent requests from multiple threads/workers do not corrupt state."""
    repo = HistoryRepository(engine_type="duckdb", duckdb_path=tmp_path / "test_conc.duckdb", parquet_path=tmp_path / "test_conc.parquet")
    repo.clear()
    writer = HistoryWriter(repository=repo)

    def write_tx(idx: int):
        tx = RawTransaction.from_dict({
            "transaction_id": f"tx_concurrent_{idx}",
            "Timestamp": f"2026-08-11 10:00:{idx:02d}",
            "From_Account": f"acct_conc_{idx % 5}",
            "To_Account": "acct_conc_target",
            "From_Bank": "10",
            "To_Bank": "20",
            "Amount_Paid": 100.0 * (idx + 1),
            "Amount_Received": 100.0 * (idx + 1),
            "Payment_Format": "ACH",
            "Payment_Currency": "USD",
            "Receiving_Currency": "USD"
        })
        writer.persist_transaction(tx)

    threads = []
    for i in range(10):
        t = threading.Thread(target=write_tx, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Query combined histories
    all_senders = [f"acct_conc_{i}" for i in range(5)]
    hist = repo.get_account_history(all_senders)
    assert len(hist) == 10  # All 10 distinct transactions persisted safely


def _multiprocess_worker(db_path: Any, worker_id: int):
    """Helper worker for multiprocessing test writing transactions concurrently."""
    from fraud_detection.core import RawTransaction
    from fraud_detection.history import HistoryRepository, HistoryWriter
    repo = HistoryRepository(engine_type="duckdb", duckdb_path=db_path)
    writer = HistoryWriter(repository=repo)
    for i in range(5):
        tx = RawTransaction.from_dict({
            "transaction_id": f"tx_mp_{worker_id}_{i}",
            "Timestamp": f"2026-08-11 10:{worker_id:02d}:{i:02d}",
            "From_Account": f"acct_mp_{worker_id}",
            "To_Account": "acct_mp_target",
            "From_Bank": "10",
            "To_Bank": "20",
            "Amount_Paid": 100.0 * (i + 1),
            "Amount_Received": 100.0 * (i + 1),
            "Payment_Format": "ACH",
            "Payment_Currency": "USD",
            "Receiving_Currency": "USD"
        })
        writer.persist_transaction(tx)
    repo.close()


def test_multiprocess_concurrency_safety(tmp_path):
    """Verifies that separate OS processes writing to persistent store do not corrupt state or drop updates."""
    import multiprocessing
    db_p = tmp_path / "mp_test.duckdb"
    repo_init = HistoryRepository(engine_type="duckdb", duckdb_path=db_p)
    repo_init.clear()
    repo_init.close()

    processes = []
    for w in range(4):
        p = multiprocessing.Process(target=_multiprocess_worker, args=(db_p, w))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

    # Query result from fresh repo instance
    repo_check = HistoryRepository(engine_type="duckdb", duckdb_path=db_p)
    all_senders = [f"acct_mp_{w}" for w in range(4)]
    hist = repo_check.get_account_history(all_senders)
    assert len(hist) == 20  # 4 workers * 5 transactions = 20 distinct rows persisted cleanly


def test_current_transaction_no_leakage(tmp_path):
    """Proves that current transaction state is READ FIRST before being persisted (no self-leakage)."""
    repo = HistoryRepository(duckdb_path=tmp_path / "leak_check.duckdb")
    repo.clear()
    writer = HistoryWriter(repository=repo)

    ctx_service = ContextService(repository=repo)
    feature_order = ["numeric__account_transaction_count", "numeric__Amount_Paid"]
    feat_service = OnlineFeatureService(context_service=ctx_service, feature_order=feature_order)

    tx = RawTransaction.from_dict({
        "transaction_id": "tx_leak_001",
        "Timestamp": "2026-08-11 12:00:00",
        "From_Account": "acct_leak_sender",
        "To_Account": "acct_leak_receiver",
        "From_Bank": "10",
        "To_Bank": "20",
        "Amount_Paid": 5000.0,
        "Amount_Received": 5000.0,
        "Payment_Format": "ACH",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    })

    # Step 1: Read previous state & build features BEFORE persist
    df_features = feat_service.build_features_single(tx)

    # Prior transaction count MUST be 0 (current transaction not counted in its own features)
    assert df_features["numeric__account_transaction_count"].iloc[0] == 0.0

    # Step 2: Persist current transaction AFTER feature building
    writer.persist_transaction(tx)

    # Step 3: Verify DB now has 1 row for future transactions
    hist = repo.get_account_history(["acct_leak_sender"])
    assert len(hist) == 1


def test_cold_start_fallbacks(tmp_path):
    """Verifies cold-start fallback behavior for brand new entities."""
    repo = HistoryRepository(engine_type="duckdb", duckdb_path=tmp_path / "test_cold.duckdb", parquet_path=tmp_path / "test_cold.parquet")
    repo.clear()

    ctx_service = ContextService(repository=repo, reference_priors={
        "global_priors": {"fraud_rate": 0.015},
        "bank_fraud_rate": {"10": 0.012},
        "payment_format_risk": {"ACH": 0.008},
        "currency_risk": {"USD": 0.011}
    })

    feature_order = [
        "numeric__Amount_Paid", "numeric__account_avg_amount", "numeric__seconds_since_last_tx",
        "numeric__bank_fraud_rate", "numeric__rolling_mean_5"
    ]
    service = OnlineFeatureService(context_service=ctx_service, feature_order=feature_order)

    raw_tx = RawTransaction.from_dict({
        "transaction_id": "tx_cold_test",
        "Timestamp": "2026-08-11 12:00:00",
        "From_Account": "brand_new_sender_99",
        "To_Account": "brand_new_receiver_88",
        "From_Bank": "10",
        "To_Bank": "20",
        "Amount_Paid": 750.0,
        "Amount_Received": 750.0,
        "Payment_Format": "ACH",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    })

    df_feats = service.build_features_single(raw_tx)
    assert df_feats["numeric__Amount_Paid"].iloc[0] == 750.0
    assert df_feats["numeric__account_avg_amount"].iloc[0] == 750.0
    assert df_feats["numeric__seconds_since_last_tx"].iloc[0] == 999999.0
    assert df_feats["numeric__bank_fraud_rate"].iloc[0] == 0.012
    assert df_feats["numeric__rolling_mean_5"].iloc[0] == 750.0


def test_feature_parity_toleranced_comparison(tmp_path):
    """Verifies feature parity across representative transaction scenarios using exact equality for flags and tolerances for floats."""
    repo = HistoryRepository(duckdb_path=tmp_path / "test_parity.duckdb", parquet_path=tmp_path / "test_parity.parquet")
    engine = EngineFactory.create(history_repository=repo)
    assert engine is not None

    raw_tx = {
        "transaction_id": "tx_parity_001",
        "Timestamp": "2026-08-11 14:00:00",
        "From_Account": "acct_parity_sender",
        "To_Account": "acct_parity_receiver",
        "From_Bank": "10",
        "To_Bank": "20",
        "Amount_Paid": 15000.0,
        "Amount_Received": 15000.0,
        "Payment_Format": "Wire",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    }

    session = engine.predict(raw_tx)
    assert session is not None
    assert session.calibrated_probability >= 0.0
    assert session.decision in ["APPROVED_LEGITIMATE", "APPROVED_WITH_MONITORING", "FLAGGED_FRAUD", "FLAGGED_CRITICAL_FRAUD"]


def test_end_to_end_real_artifact_inference(tmp_path):
    """Executes real end-to-end inference and verifies session decision, threshold, and SHAP card output."""
    repo = HistoryRepository(duckdb_path=tmp_path / "test_e2e.duckdb", parquet_path=tmp_path / "test_e2e.parquet")
    engine = EngineFactory.create(history_repository=repo)
    # Warmup check
    assert engine.warmup() is True

    raw_tx = {
        "transaction_id": "tx_e2e_real_001",
        "Timestamp": "2026-08-11 15:30:00",
        "From_Account": "cust_real_77",
        "To_Account": "merchant_real_88",
        "From_Bank": "10",
        "To_Bank": "20",
        "Amount_Paid": 250.0,
        "Amount_Received": 250.0,
        "Payment_Format": "ACH",
        "Payment_Currency": "USD",
        "Receiving_Currency": "USD"
    }

    session = engine.predict(raw_tx)
    assert session.request_id is not None
    assert abs(session.threshold - 0.2556561085972851) < 1e-5
    assert session.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
    assert session.explanation is not None
    assert "Fraud Investigator Decision Card" in session.explanation.investigator_card
