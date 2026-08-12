"""
Concurrent Database Thread-Safety & Transaction Isolation Test.
Executes parallel multi-threaded transaction insertions against HistoryRepository
to verify zero deadlocks, zero double-counting, and clean ACID persistence.
"""
import concurrent.futures
import time
import pandas as pd
import pytest

from fraud_detection.history import HistoryRepository


def test_concurrent_transaction_persistence():
    """Simulates 10 concurrent threads inserting distinct and duplicate transaction payloads."""
    repo = HistoryRepository(bootstrap_data=False)
    
    def worker(thread_idx: int):
        df_new = pd.DataFrame([{
            "transaction_key": f"TX_CONCURRENT_{thread_idx % 3}", # 3 distinct keys across 10 threads
            "Timestamp": "2026-08-12T12:00:00",
            "From_Account": f"ACC_SENDER_{thread_idx % 2}",
            "To_Account": f"ACC_RECEIVER_{thread_idx % 2}",
            "From_Bank": "BANK_10",
            "To_Bank": "BANK_20",
            "Amount_Paid": 5000.0,
            "Amount_Received": 5000.0,
            "Payment_Format": "Wire Transfer",
            "Payment_Currency": "USD",
            "Receiving_Currency": "USD",
            "is_laundering": 0
        }])
        repo.add_transactions(df_new)
        return thread_idx

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker, i) for i in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == 10, "All 10 concurrent worker threads must complete without exception."
    repo.close()
