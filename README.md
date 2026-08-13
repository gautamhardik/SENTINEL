# 🛡️ SENTINEL RISK ENGINE
### Real-Time Financial Transaction Fraud Screening & Explainability Instrument

[![Live Demo](https://img.shields.io/badge/Live%20Demo-sentinelhg.vercel.app-indigo.svg)](https://sentinelhg.vercel.app/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14.2-black.svg)](https://nextjs.org/)
[![LightGBM](https://img.shields.io/badge/Model-LightGBM%20Champion-brightgreen.svg)](models/champion/)
[![Docker Compose](https://img.shields.io/badge/Docker-Compose-blue.svg)](docker-compose.yml)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2015-336791.svg)](https://www.postgresql.org/)
[![ARM64 Compatible](https://img.shields.io/badge/ARM64-Oracle%20Ampere%20A1-purple.svg)](Dockerfile)
[![Production Audit](https://img.shields.io/badge/Production%20Audit-Passed-emerald.svg)](docs/Validation_Framework.md)

---

## 🖥️ Workstation Interface Showcase

| Single-Transaction Risk Screening Form | Calibrated Risk Assessment & SHAP Drivers |
| :---: | :---: |
| ![Screening Form](docs/assets/hero_screening.png) | ![Risk Results & SHAP Drivers](docs/assets/risk_results.png) |

---

## 📌 Executive Product Overview

**Sentinel Risk Engine** is a single-transaction financial fraud screening instrument designed for high-throughput banking environments. Given **11 raw transaction fields**, the backend executes online feature engineering across prior account history, standardizes a **61-feature vector**, scores the transaction with an Optuna-tuned **LightGBM Champion Model**, calibrates probabilities using **Isotonic Regression**, evaluates an unrounded cost-optimized **decision threshold (`0.2556561085972851`)**, and computes **TreeSHAP risk drivers** for instant investigator transparency.

### Key Architectural Invariants
- **Strict Anti-Dashboard Rule**: Zero noise, zero sidebars, zero trend grids—100% focused on single-transaction risk assessment.
- **11-Field Public Contract**: Frontend submits *only* raw transaction details; feature engineering, scaling, SHAP, and decisions are 100% backend-owned.
- **Isotonic Calibration**: Converts raw tree margin outputs into mathematically calibrated posterior fraud probabilities ($P \in [0, 1]$).
- **Dual-Store Resilience**: Primary velocity state backed by PostgreSQL 15, with thread-safe DuckDB fallback for local offline operation.

---

## 📊 Champion Model Metrics & Validation

Evaluated on an independent test dataset of **~210,000 transactions** (15% test split of 1.4M dataset):

| Metric | Champion Value | Target / Benchmark | Status |
| :--- | :---: | :---: | :---: |
| **ROC-AUC** | **0.9698** | $\ge 0.9000$ | PASS |
| **PR-AUC** | **0.8486** | $\ge 0.7500$ | PASS |
| **F1-Score (at $T=0.2557$)** | **0.7646** | $\ge 0.7000$ | PASS |
| **Fraud Recall (Capture Rate)** | **76.00%** | $\ge 70.00\%$ | PASS |
| **Inference Latency** | **< 25 ms** | $\le 50.0$ ms | PASS |

---

## 💡 Key Discoveries & Technical Design Decisions

1. **Cost-Weighted Threshold Optimization ($T = 0.2556561085972851$)**:
   - Standard 0.50 classification thresholds fail in fraud detection due to asymmetric business costs. In banking, a **False Negative (missed fraud)** costs $\approx \$500$, while a **False Positive (unnecessary hold)** costs $\approx \$15$ in manual review overhead.
   - We ran grid optimization over empirical loss functions: $L(T) = 500 \cdot FN(T) + 15 \cdot FP(T)$. The global minimum loss occurred at $T \approx 0.2556561085972851$, yielding **76.0% fraud capture** while restricting false positive review rates to manageable compliance bounds.

2. **Isotonic Regression over Platt Scaling**:
   - Non-parametric Isotonic Calibration outperformed Sigmoid/Platt scaling because GBDT leaf distributions exhibit non-linear step-function clustering near boundary edges. Isotonic regression preserved monotonic ordering while correcting tree overconfidence.

3. **Cold-Start Account Velocity Priors**:
   - First-time unobserved sender accounts attempting high-value transfers ($\ge \$25,000$) initial default to `delta_sec = 300.0` (5 minutes rapid prior), forcing immediate velocity risk flags rather than inheriting low-risk long-inactivity imputation (`999,999` seconds).

---

## 🏛️ End-to-End System Architecture

```text
                                  ┌────────────────────────────────┐
                                  │      Browser Workstation       │
                                  │  Next.js 14 Single-Form Client │
                                  └───────────────┬────────────────┘
                                                  │
                                                  │ POST /api/v1/predict (11 Raw Fields)
                                                  ▼
                                  ┌────────────────────────────────┐
                                  │   FastAPI Backend Container    │
                                  │    (Port 8000 / Python 3.11)   │
                                  └───────────────┬────────────────┘
                                                  │
                  ┌───────────────────────────────┼───────────────────────────────┐
                  │                               │                               │
                  ▼                               ▼                               ▼
       ┌─────────────────────┐        ┌─────────────────────┐        ┌─────────────────────┐
       │ PostgreSQL 15 DB    │        │  61-Feature Online  │        │ LightGBM Champion   │
       │ Transaction History │───────►│  Feature Pipeline   │───────►│ Inference Model     │
       │ & Account States    │        │ (Velocity/Outliers) │        │ (model_v1.joblib)   │
       └─────────────────────┘        └─────────────────────┘        └──────────┬──────────┘
                                                                                │
                                                                                ▼
       ┌─────────────────────┐        ┌─────────────────────┐        ┌─────────────────────┐
       │ Next.js Result View │        │ TreeSHAP Engine     │        │ Isotonic Calibrator │
       │ Investigator Report │◄───────│ Key Risk Drivers &  │◄───────│ Probability &       │
       │ & Action Guidance   │        │ Feature Attribution │        │ Threshold Evaluation│
       └─────────────────────┘        └─────────────────────┘        └─────────────────────┘
```

---

## ⚖️ Authoritative 4-Tier Decision Policy

The backend evaluates calibrated fraud probability $P$ against the exact cost-optimized threshold ($T = 0.2556561085972851$):

| Calibrated Fraud Probability ($P$) | Risk Tier | System Decision | Action Code | Operator / Boundary |
|---|---|---|---|---|
| $0.0\% \le P < 10.0\%$ | `LOW` | `APPROVED_LEGITIMATE` | `APPROVE` | $P < 0.10$ |
| $10.0\% \le P < 25.5656\%$ | `MEDIUM` | `APPROVED_WITH_MONITORING` | `MONITOR` | $0.10 \le P < 0.255656$ |
| $25.5656\% \le P < 75.0\%$ | `HIGH` | `FLAGGED_FRAUD` | `HOLD_FOR_MANUAL_INVESTIGATION` | $0.255656 \le P < 0.75$ |
| $75.0\% \le P \le 100.0\%$ | `CRITICAL` | `FLAGGED_CRITICAL_FRAUD` | `DECLINE_IMMEDIATELY` | $P \ge 0.75$ |

*Comparison Logic*: `probability >= threshold` evaluates as `FLAGGED_FRAUD`.

---

## ⚡ Quickstart — 1-Command Production Deployment

Deploy the complete containerized Sentinel Risk Engine 3-tier stack via Docker Compose:

```bash
# 1. Clone repository & enter directory
git clone https://github.com/gautamhardik/SENTINEL.git
cd SENTINEL

# 2. Configure environment
cp .env.example .env

# 3. Build & start containers in detached mode
docker compose build
docker compose up -d

# 4. Verify system readiness
curl http://localhost:8000/health/ready

# 5. Open Next.js Workstation in browser
open http://localhost:3000
```

---

## 📡 API Specification & Payload Contract

### `POST /api/v1/predict`

#### Request Payload (Raw 11 Fields Only)
```json
{
  "transaction_id": "TX-89201492",
  "Timestamp": "2026-08-12T14:30:00",
  "From_Account": "ACC_HIGH_VAL_601",
  "To_Account": "ACC_HIGH_VAL_602",
  "From_Bank": "10",
  "To_Bank": "99",
  "Amount_Paid": 75000.00,
  "Amount_Received": 75000.00,
  "Payment_Format": "Wire Transfer",
  "Payment_Currency": "USD",
  "Receiving_Currency": "USD"
}
```

#### Response Payload (Calculated Backend Output)
```json
{
  "transaction_id": "TX-89201492",
  "request_id": "req_8a92f1b04c",
  "decision": "FLAGGED_FRAUD",
  "risk_level": "HIGH",
  "calibrated_probability": 0.384210,
  "fraud_probability": 0.384210,
  "raw_probability": 0.342105,
  "threshold": 0.255656,
  "recommended_action": "HOLD_FOR_MANUAL_INVESTIGATION",
  "explanation": {
    "top_risk_drivers": [
      {
        "feature": "Amount_Paid",
        "importance": 0.8412,
        "direction": "RISK_INCREASING",
        "value": 75000.0
      },
      {
        "feature": "is_amount_outlier",
        "importance": 0.6210,
        "direction": "RISK_INCREASING",
        "value": 1.0
      }
    ],
    "investigator_card": "High-value cross-border wire transfer exceeding statistical baseline."
  },
  "inference_latency_ms": 18.52,
  "model_version": "v1.0.0",
  "timestamp": "2026-08-12T14:30:00"
}
```
*Note*: `fraud_probability` is an alias of `calibrated_probability` maintained for backward compatibility with legacy API integration contracts. `raw_probability` reflects uncalibrated GBDT margin probability prior to isotonic mapping.

---

## 📈 Concurrency & Performance Load Benchmarks

Verified via progressive load testing script ([test_postgres_load.py](tests/integration/test_postgres_load.py)):

| Worker Pool Concurrency | Total Requests | Successful Requests | Failures | Throughput (req/s) | p50 Latency (ms) | p99 Latency (ms) |
|---:|---:|---:|---:|---:|---:|---:|
| **10 Concurrent Workers** | 50 | 50 | 0 | 14.8 req/s | 62.4 ms | 185.0 ms |
| **25 Concurrent Workers** | 50 | 50 | 0 | 18.2 req/s | 118.5 ms | 310.2 ms |
| **50 Concurrent Workers** | 100 | 100 | 0 | 22.5 req/s | 210.0 ms | 610.5 ms |
| **100 Concurrent Workers** | 100 | 100 | 0 | 26.1 req/s | 385.2 ms | 1140.0 ms |

> ⚠️ **Diagnosed Performance Bottleneck**: Under high worker concurrency (>50 workers), throughput plateaus near ~26 req/s while p99 latency rises to 1.1s. Profiling confirmed this bottleneck is driven by synchronous TreeSHAP matrix calculation on single-worker Uvicorn processes and DB connection pool waiting. Mitigation via Gunicorn multi-worker processing and cached SHAP background workers is planned for v1.1.

---

## ⚠️ System Limitations & Known Scope Boundaries

1. **Synchronous SHAP Overhead**: Real-time TreeSHAP contribution generation adds ~15–20ms overhead per transaction.
2. **Tabular Scope**: Model relies strictly on tabular transaction features; graph neural embeddings and device fingerprinting are out of scope for v1.0.
3. **Batch Cold-Start Lag**: Historical velocity features for unseeded accounts depend on initial transaction persistence.

---

## 📂 Project Structure Map

```text
Fraud Detection/
├── Dockerfile                          # FastAPI Backend Production Dockerfile
├── docker-compose.yml                  # PostgreSQL, Backend, Frontend Compose Stack
├── .env.example                        # Production Environment Template
├── pyproject.toml                      # Python Dependencies & Packaging Specs
├── frontend/                           # Next.js 14 Workstation Frontend
│   ├── Dockerfile                      # Standalone Multi-Stage Next.js Dockerfile
│   └── src/                            # React Components & Workstation Views
├── models/champion/                    # Champion ML Model Artifacts
│   ├── model_v1.joblib                 # Optuna-Tuned LightGBM Champion
│   ├── calibrator_v1.joblib            # Isotonic Calibrator
│   ├── feature_order_v1.json           # 61-Feature Order Schema
│   └── threshold_v1.json               # Cost-Optimized Threshold Config
├── src/fraud_detection/                # Core Python Engine Package
│   ├── api/                            # FastAPI Application & Schemas
│   ├── history/                        # DuckDB & PostgreSQL Storage Layer
│   ├── feature_engineering/            # 61-Feature Extraction Pipeline
│   └── thresholding/                   # 4-Tier Decision Engine
└── tests/                              # Pytest Unit & Integration Suite
```

---

## 📄 License & Maintainers

Maintained by **Hardik Gautam** ([@gautamhardik](https://github.com/gautamhardik)).  
Distributed under the **MIT License**.
