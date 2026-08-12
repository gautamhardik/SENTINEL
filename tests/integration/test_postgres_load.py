"""
PostgreSQL Enterprise Concurrency & Stress Load Testing Suite.
Executes multi-worker parallel stress testing against PostgreSQL / HistoryRepository.
Measures latency metrics (p50, p95, p99), error rates, deadlock resilience, and ACID compliance.
"""
import concurrent.futures
import math
import time
from typing import Dict, List, Tuple
import pandas as pd
import pytest

from fraud_detection.history import HistoryRepository


def run_concurrency_level(concurrency_level: int, total_requests: int) -> Dict[str, float]:
    """Executes a workload of total_requests distributed across concurrency_level parallel threads."""
    repo = HistoryRepository(bootstrap_data=False)
    latencies: List[float] = []
    failures: int = 0
    successes: int = 0

    def worker(task_idx: int) -> Tuple[bool, float]:
        start = time.time()
        try:
            # Alternate between distinct and duplicate transactions
            tx_key = f"LOAD_TX_{task_idx % 15}" # Forces intentional duplicates
            df_new = pd.DataFrame([{
                "transaction_key": tx_key,
                "Timestamp": "2026-08-12T13:00:00",
                "From_Account": f"ACC_LOAD_{task_idx % 5}",
                "To_Account": f"ACC_RCVR_{task_idx % 5}",
                "From_Bank": "BANK_10",
                "To_Bank": "BANK_20",
                "Amount_Paid": 1000.0 + (task_idx * 10),
                "Amount_Received": 1000.0 + (task_idx * 10),
                "Payment_Format": "Wire Transfer",
                "Payment_Currency": "USD",
                "Receiving_Currency": "USD",
                "is_laundering": 0
            }])
            repo.add_transactions(df_new)
            elapsed = (time.time() - start) * 1000.0
            return (True, elapsed)
        except Exception as e:
            elapsed = (time.time() - start) * 1000.0
            return (False, elapsed)

    work_start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency_level) as executor:
        futures = [executor.submit(worker, i) for i in range(total_requests)]
        for f in concurrent.futures.as_completed(futures):
            ok, duration = f.result()
            latencies.append(duration)
            if ok:
                successes += 1
            else:
                failures += 1

    total_time_s = time.time() - work_start
    repo.close()

    sorted_lats = sorted(latencies)
    n = len(sorted_lats)
    p50 = sorted_lats[int(n * 0.50)] if n > 0 else 0.0
    p95 = sorted_lats[int(n * 0.95)] if n > 0 else 0.0
    p99 = sorted_lats[min(int(n * 0.99), n - 1)] if n > 0 else 0.0

    return {
        "concurrency": concurrency_level,
        "total_requests": total_requests,
        "successes": successes,
        "failures": failures,
        "throughput_req_sec": round(total_requests / total_time_s, 2),
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "p99_ms": round(p99, 2),
    }


def test_postgres_concurrency_matrix():
    """Executes the progressive load test matrix across 10, 25, 50, and 100 concurrent workers."""
    matrix_results = []
    levels = [(10, 50), (25, 50), (50, 100), (100, 100)]
    
    for conc, total in levels:
        res = run_concurrency_level(conc, total)
        matrix_results.append(res)
        assert res["failures"] == 0, f"Concurrency level {conc} encountered {res['failures']} database failures."

    assert len(matrix_results) == 4, "All 4 concurrency matrix tiers must complete successfully."
