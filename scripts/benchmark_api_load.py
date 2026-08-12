"""
Load Testing & Performance Benchmarking Script for Fraud Detection FastAPI Service.
Executes concurrent async HTTP POST requests to /api/v1/predict at 1, 10, 50, and 100 concurrency levels.
Calculates Mean, p95, p99 latencies, throughput (req/sec), error rate, and RAM usage.
"""
import asyncio
import sys
import time

import httpx
import numpy as np
import psutil

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

API_URL = "http://localhost:8000/api/v1/predict"

SAMPLE_PAYLOAD = {
    "Amount_Paid": 1250.0,
    "Amount_Received": 1250.0,
    "From_Account": "Acc_10293",
    "To_Account": "Acc_99481",
    "From_Bank": "Bank_A",
    "To_Bank": "Bank_B",
    "Payment_Format": "ACH",
    "Payment_Currency": "USD",
    "Receiving_Currency": "USD"
}

async def send_request(client: httpx.AsyncClient) -> tuple[float, bool]:
    start = time.time()
    try:
        response = await client.post(API_URL, json=SAMPLE_PAYLOAD, timeout=10.0)
        dur_ms = (time.time() - start) * 1000.0
        success = response.status_code == 200 and response.json().get("success") is True
        return dur_ms, success
    except Exception:
        dur_ms = (time.time() - start) * 1000.0
        return dur_ms, False

async def run_load_test(concurrency: int, total_requests: int):
    print(f"\n⚡ Running Load Benchmark: {concurrency} Concurrent Workers | {total_requests} Total Requests...")

    limits = httpx.Limits(max_keepalive_connections=concurrency + 10, max_connections=concurrency + 20)
    async with httpx.AsyncClient(limits=limits) as client:
        # Measure initial RAM
        process = psutil.Process()
        ram_before_mb = process.memory_info().rss / (1024 * 1024)

        start_time = time.time()

        tasks = [send_request(client) for _ in range(total_requests)]
        results = await asyncio.gather(*tasks)

        total_time_sec = time.time() - start_time
        ram_after_mb = process.memory_info().rss / (1024 * 1024)

    latencies = [r[0] for r in results]
    successes = [r[1] for r in results]

    successful_count = sum(successes)
    failed_count = total_requests - successful_count
    error_rate = (failed_count / total_requests) * 100.0

    mean_lat = float(np.mean(latencies))
    p50_lat = float(np.percentile(latencies, 50))
    p95_lat = float(np.percentile(latencies, 95))
    p99_lat = float(np.percentile(latencies, 99))
    throughput = total_requests / total_time_sec

    print(f"| Concurrency: {concurrency:3d} | Total Time: {total_time_sec:.2f}s | Throughput: {throughput:6.2f} req/s | Error Rate: {error_rate:4.1f}% |")
    print(f"  └─ Latency -> Mean: {mean_lat:6.2f} ms | p50: {p50_lat:6.2f} ms | p95: {p95_lat:6.2f} ms | p99: {p99_lat:6.2f} ms")
    print(f"  └─ RAM Footprint -> {ram_after_mb:.2f} MB (Delta: {ram_after_mb - ram_before_mb:+.2f} MB)")

    return {
        "concurrency": concurrency,
        "total_requests": total_requests,
        "throughput_req_sec": round(throughput, 2),
        "error_rate_pct": round(error_rate, 2),
        "mean_latency_ms": round(mean_lat, 2),
        "p50_latency_ms": round(p50_lat, 2),
        "p95_latency_ms": round(p95_lat, 2),
        "p99_latency_ms": round(p99_lat, 2),
        "ram_usage_mb": round(ram_after_mb, 2)
    }

async def main():
    print("=" * 70)
    print("🚀 FASTAPI LOAD & PERFORMANCE BENCHMARK (CONCURRENT REQUESTS)")
    print("=" * 70)

    # Warmup request
    async with httpx.AsyncClient() as client:
        await send_request(client)

    results = []
    results.append(await run_load_test(concurrency=1, total_requests=100))
    results.append(await run_load_test(concurrency=10, total_requests=200))
    results.append(await run_load_test(concurrency=50, total_requests=500))
    results.append(await run_load_test(concurrency=100, total_requests=1000))

    print("\n" + "=" * 70)
    print("✅ BENCHMARK COMPLETE!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
