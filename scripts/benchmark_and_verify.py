"""
Script for Stage 10 (Inference Pipeline Integration), Stage 11 (Benchmarking),
and Stage 12 (Artifact Integrity Check).
"""
import json
import os
import sys
import time
import tracemalloc

import joblib
import numpy as np
import pandas as pd

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("=" * 60)
    print("STAGE 10, 11 & 12: INFERENCE INTEGRATION, BENCHMARKING & INTEGRITY")
    print("=" * 60)

    # STAGE 12: ARTIFACT INTEGRITY CHECK
    print("\n--- STAGE 12: ARTIFACT INTEGRITY CHECK ---")
    registry_path = "models/registry.json"
    assert os.path.exists(registry_path), f"Registry file missing: {registry_path}"

    with open(registry_path, "r") as f:
        reg = json.load(f)

    champ_path = reg.get("artifact_directory", "models/champion")
    expected_assets = reg.get("artifacts", {})
    print(f"Registry Version: {reg.get('champion_model_version', 'unknown')}")

    for key, asset in expected_assets.items():
        asset_path = os.path.join(champ_path, asset)
        assert os.path.exists(asset_path), f"Required champion asset missing: {asset_path}"
        print(f"  [OK] Asset '{key}' present: {asset}")

    model_file = expected_assets.get("model", "model_v1.joblib")
    calibrator_file = expected_assets.get("calibrator", "calibrator_v1.joblib")
    feature_order_file = expected_assets.get("feature_order", "feature_order_v1.json")
    threshold_file = expected_assets.get("threshold", "threshold_v1.json")

    model = joblib.load(os.path.join(champ_path, model_file))
    calibrator = joblib.load(os.path.join(champ_path, calibrator_file))

    with open(os.path.join(champ_path, feature_order_file), "r") as f:
        feature_order = json.load(f)

    with open(os.path.join(champ_path, threshold_file), "r") as f:
        threshold_info = json.load(f)

    print(f"\nModel Loaded: {type(model).__name__}")
    print(f"Calibrator Loaded: {type(calibrator).__name__}")
    print(f"Feature Count: {len(feature_order)}")
    print(f"Optimal Threshold: {threshold_info.get('optimal_threshold', threshold_info.get('decision_threshold', 0.5)):.4f}")

    # STAGE 10 & 11: INFERENCE INTEGRATION & BENCHMARKING
    print("\n--- STAGE 10 & 11: INFERENCE INTEGRATION & BENCHMARKING ---")
    tracemalloc.start()
    t_start = time.time()

    # Generate dummy transaction vector matching 61 features
    single_tx_df = pd.DataFrame([{col: float(np.random.randn()) for col in feature_order}])
    batch_100_df = pd.DataFrame([{col: float(np.random.randn()) for col in feature_order} for _ in range(100)])
    batch_1000_df = pd.DataFrame([{col: float(np.random.randn()) for col in feature_order} for _ in range(1000)])

    # Single tx prediction benchmark
    t0 = time.time()
    raw_score = model.predict_proba(single_tx_df)[:, 1][0]
    cal_score = calibrator.predict_proba(single_tx_df)[:, 1][0]
    single_tx_latency_ms = (time.time() - t0) * 1000.0

    # Batch 100 benchmark
    t0 = time.time()
    _ = calibrator.predict_proba(batch_100_df)[:, 1]
    batch_100_latency_ms = (time.time() - t0) * 1000.0

    # Batch 1000 benchmark
    t0 = time.time()
    _ = calibrator.predict_proba(batch_1000_df)[:, 1]
    batch_1000_latency_ms = (time.time() - t0) * 1000.0

    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"Single Tx Inference Latency: {single_tx_latency_ms:.2f} ms")
    print(f"Batch (100 Tx) Latency:       {batch_100_latency_ms:.2f} ms ({batch_100_latency_ms/100:.3f} ms/tx)")
    print(f"Batch (1000 Tx) Latency:      {batch_1000_latency_ms:.2f} ms ({batch_1000_latency_ms/1000:.3f} ms/tx)")
    print(f"Peak Memory Consumption:      {peak_mem / (1024 * 1024):.2f} MB")

    # Save benchmark metrics to json
    bench_results = {
        "single_tx_latency_ms": single_tx_latency_ms,
        "batch_100_latency_ms": batch_100_latency_ms,
        "batch_1000_latency_ms": batch_1000_latency_ms,
        "batch_1000_per_tx_ms": batch_1000_latency_ms / 1000.0,
        "peak_memory_mb": peak_mem / (1024 * 1024),
        "tested_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    with open("reports/benchmark_metrics.json", "w") as f:
        json.dump(bench_results, f, indent=2)

    print("\n✅ STAGE 10, 11 & 12 COMPLETE!")

if __name__ == "__main__":
    main()
