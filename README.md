# 🛡️ SENTINEL RISK ENGINE
### Real-Time Financial Transaction Fraud Screening & Explainability Instrument

<div align="center">

[![Live Demo](https://img.shields.io/badge/Live%20Demo-sentinelhg.vercel.app-6366f1)](https://sentinelhg.vercel.app/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-000000?logo=next.js&logoColor=white)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](docker-compose.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

**A production-grade, end-to-end ML system** that screens financial transactions for fraud in real time — complete with calibrated risk probabilities, TreeSHAP explainability, a 4-tier decision policy, and a live interactive workstation.

[**Try the Live Demo**](https://sentinelhg.vercel.app/) · [**API Docs**](#api-specification--payload-contract) · [**Quickstart**](#quickstart--1-command-deployment) · [**Architecture**](#system-architecture)

</div>

---

Demo Video

https://github.com/user-attachments/assets/88cbdd3f-6728-4cfc-9883-a144aa900407

---



## Live Workstation

| Transaction Risk Screening Form | Calibrated Risk Assessment & SHAP Drivers |
| :---: | :---: |
| ![Screening Form](docs/assets/hero_screening.png) | ![Risk Results & SHAP Drivers](docs/assets/risk_results.png) |

---

## What This Is

**Sentinel Risk Engine** is a production-grade single-transaction fraud screening instrument built for high-throughput banking environments. A user submits **11 raw transaction fields** and the system returns a calibrated fraud probability, 4-tier risk decision, and ranked SHAP driver card — all in under 25 ms.

**Why this architecture matters:**
- **No dashboard tax** — Zero chart grids, zero sidebar noise. Every pixel is focused on the risk assessment for the transaction in front of the investigator.
- **Clean API contract** — Frontend submits only raw fields. Feature engineering, calibration, SHAP, and decisions are 100% backend-owned and cannot be spoofed by the client.
- **Production-honest ML** — Cost-optimized threshold tuned on a real business loss function, not the default 0.50 argmax.

---

## Champion Model Performance

Evaluated on a held-out independent test partition of **~302,000 transactions** (15% temporal split of the 2.0M-row IBM AML dataset):

| Metric | Value | Benchmark | Status |
|:---|:---:|:---:|:---:|
| ROC-AUC | 0.9689 | ≥ 0.9000 | PASS |
| PR-AUC | 0.6574 | ≥ 0.6000 | PASS |
| F1-Score (at T = 0.2557) | 0.6560 | ≥ 0.6000 | PASS |
| Fraud Recall / Capture Rate | 75.7% | ≥ 70.0% | PASS |
| Inference Latency | < 25 ms | ≤ 50 ms | PASS |

> All values read directly from [`models/champion/metadata_v1.json`](models/champion/metadata_v1.json) and [`models/champion/threshold_v1.json`](models/champion/threshold_v1.json) — the deployed production artifacts.

---

## Dataset

| Property | Detail |
|:---|:---|
| Name | IBM Transactions for Anti Money Laundering (AML) — LI-Large variant |
| Source | [IBM AML Dataset — Kaggle](https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml) |
| Total Rows | ~2.01M transactions |
| Fraud Rate | ~0.1% (extreme class imbalance) |
| Split | 70% train / 15% validation / 15% test (temporal ordering preserved) |
| Train Rows | 1,409,294 |
| Validation Rows | 301,991 |
| Test Rows | 301,993 |
| Raw Features | 11 (account IDs, banks, amounts, currencies, payment format, timestamp) |
| Engineered Features | 61 (velocity stats, outlier flags, cross-currency indicators, rolling aggregates) |

> The temporal split ensures no future data leaks into training — account velocity features are computed strictly from transaction history preceding each evaluation window.

---

## Key Technical Design Decisions

### 1. Cost-Weighted Threshold Optimization (T = 0.2556561085972851)

Standard 0.50 classification thresholds fail in fraud detection because of asymmetric business costs. Using a domain-realistic cost matrix:

```
L(T) = 500 × FN(T) + 15 × FP(T)
```

| Cost Type | Assumed Unit Cost | Rationale |
|:---|:---:|:---|
| False Negative (missed fraud) | $500 | Average fraud loss per undetected transaction |
| False Positive (unnecessary hold) | $15 | Manual investigator review overhead |

Grid-optimizing `L(T)` over the validation set located the minimum at **T = 0.2556561085972851**, yielding **75.7% fraud capture** while keeping false-positive review rates within compliance bounds. Cost parameters are defined in [`configs/ml_config.yaml`](configs/ml_config.yaml) and consumed by the live `ThresholdOptimizer` class.

### 2. Isotonic Calibration over Platt Scaling

Isotonic Regression was selected over Sigmoid/Platt scaling because Platt's linear sigmoid boundary is known to underfit the non-linear step-function clustering of GBDT leaf probability distributions near boundary edges. Isotonic regression preserves monotonic ordering while correcting tree overconfidence without imposing a parametric shape constraint.

The fitted calibrator is persisted at [`models/champion/calibrator_v1.joblib`](models/champion/calibrator_v1.joblib) and is the only transformation applied between the raw LightGBM margin score and the `calibrated_probability` returned in the API response.

### 3. Cold-Start Account Velocity Priors

First-time unobserved sender accounts attempting high-value transfers (≥ $25,000) default to `delta_sec = 300.0` (5-minute rapid prior), forcing immediate velocity risk flags rather than inheriting low-risk long-inactivity imputation (`999,999` seconds). This eliminates the cold-start loophole where a new account could evade velocity checks on first contact.

### 4. Dual-Store Resilience

| Mode | Store | Use Case |
|:---|:---|:---|
| Production | PostgreSQL 15 | Live transaction history, ACID compliance, concurrent writes |
| Offline / Fallback | DuckDB (in-process) | Local development, CI testing, PostgreSQL failure recovery |

The `HistoryRepository` switches transparently between backends via the `DB_ENGINE_TYPE` environment variable — no application code changes required.

---

## System Architecture

```
                              ┌────────────────────────────────┐
                              │      Browser Workstation       │
                              │  Next.js 14 Single-Form Client │
                              └───────────────┬────────────────┘
                                              │
                                              │  POST /api/v1/predict (11 Raw Fields)
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
   │ & Action Guidance   │        │ Feature Attribution │        │ Threshold Decision  │
   └─────────────────────┘        └─────────────────────┘        └─────────────────────┘
```

---

## Tech Stack

### Backend

| Component | Technology | Version |
|:---|:---|:---|
| API Framework | FastAPI + Uvicorn | ≥ 0.100.0 |
| ML Model | LightGBM (Optuna-tuned) | ≥ 4.3.0 |
| Calibration | scikit-learn `CalibratedClassifierCV` (Isotonic) | ≥ 1.4.0 |
| Explainability | SHAP (TreeSHAP) | ≥ 0.44.0 |
| Primary Store | PostgreSQL 15 via psycopg2 | 15-alpine |
| Offline Store | DuckDB (in-process OLAP) | ≥ 0.10.0 |
| Data Processing | Pandas + Polars + NumPy | Latest stable |
| Hyperparameter Tuning | Optuna | Embedded in training pipeline |
| Serialization | joblib | ≥ 1.3.0 |
| Config | Pydantic v2 + PyYAML | ≥ 2.5.0 |

### Frontend

| Component | Technology |
|:---|:---|
| Framework | Next.js 14 (App Router) |
| Runtime | Node.js 20 |
| Deployment | Vercel — [sentinelhg.vercel.app](https://sentinelhg.vercel.app/) |

### Infrastructure & Quality

| Component | Technology |
|:---|:---|
| Containerization | Docker + Docker Compose v3.8 |
| Architecture | ARM64-compatible (Oracle Ampere A1) |
| Linting | Ruff |
| Type Checking | mypy |
| Testing | pytest + pytest-cov |
| Pre-commit | pre-commit hooks |

---

## 4-Tier Decision Policy

The backend evaluates calibrated probability `P` against the cost-optimized threshold `T = 0.2556561085972851`:

| Calibrated Probability (P) | Risk Tier | Decision | Action | Boundary |
|:---|:---:|:---|:---|:---|
| 0% ≤ P < 10% | `LOW` | `APPROVED_LEGITIMATE` | `APPROVE` | P < 0.10 |
| 10% ≤ P < 25.57% | `MEDIUM` | `APPROVED_WITH_MONITORING` | `MONITOR` | 0.10 ≤ P < T |
| 25.57% ≤ P < 75% | `HIGH` | `FLAGGED_FRAUD` | `HOLD_FOR_MANUAL_INVESTIGATION` | T ≤ P < 0.75 |
| 75% ≤ P ≤ 100% | `CRITICAL` | `FLAGGED_CRITICAL_FRAUD` | `DECLINE_IMMEDIATELY` | P ≥ 0.75 |

*Comparison logic*: `probability >= threshold` → `FLAGGED_FRAUD`. The threshold is loaded at startup from [`models/champion/threshold_v1.json`](models/champion/threshold_v1.json) — never hardcoded.

---

## Quickstart — 1-Command Deployment

Deploy the full 3-container stack (PostgreSQL 15 + FastAPI backend + Next.js frontend):

```bash
# 1. Clone repository
git clone https://github.com/gautamhardik/SENTINEL.git
cd SENTINEL

# 2. Configure environment
cp .env.example .env
# Edit .env to customise POSTGRES_PASSWORD if needed

# 3. Build and launch all containers
docker compose build
docker compose up -d

# 4. Verify backend health
curl http://localhost:8000/health/ready

# 5. Open the workstation
open http://localhost:3000   # macOS / Linux
```

> **Prerequisites**: Docker Desktop ≥ 24.0, Docker Compose ≥ 2.0

### Environment Variables

| Variable | Default | Description |
|:---|:---|:---|
| `DB_ENGINE_TYPE` | `postgresql` | `postgresql` for prod, `duckdb` for local dev |
| `POSTGRES_HOST` | `postgres` | PostgreSQL hostname |
| `POSTGRES_DB` | `fraud_detection` | Database name |
| `POSTGRES_USER` | `sentinel_user` | DB username |
| `POSTGRES_PASSWORD` | *(set in .env)* | DB password |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend URL consumed by the frontend |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

### Local Development (no Docker)

```bash
# Install Python dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

# Start DuckDB-backed backend (no PostgreSQL needed)
DB_ENGINE_TYPE=duckdb uvicorn src.fraud_detection.api.app:app --reload --port 8000

# In a separate terminal — start the frontend
cd frontend && npm install && npm run dev
# → http://localhost:3000
```

---

## API Specification & Payload Contract

### `POST /api/v1/predict`

Accepts exactly 11 raw transaction fields. All 61-feature engineering, calibration, SHAP, and decisions happen server-side.

#### Request Payload

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

**Valid `Payment_Format`**: `Wire Transfer` · `ACH Outbound` · `Cheque` · `Credit Card` · `Cash Deposit`
**Valid currencies**: `USD` · `EUR` · `GBP` · `CAD` · `AUD`

#### Response Payload

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
  "calibration_method": "Isotonic Regression",
  "timestamp": "2026-08-12T14:30:00"
}
```

> `fraud_probability` is an alias of `calibrated_probability` maintained for backward compatibility. `raw_probability` is the uncalibrated LightGBM margin output, prior to isotonic mapping.

### Other Endpoints

| Method | Path | Description |
|:---|:---|:---|
| `GET` | `/health` | Liveness probe |
| `GET` | `/health/ready` | Readiness probe (model + DB loaded) |
| `GET` | `/docs` | Interactive Swagger UI |
| `GET` | `/redoc` | ReDoc API reference |

---

## Concurrency & Load Benchmarks

Progressive stress test ([`tests/integration/test_postgres_load.py`](tests/integration/test_postgres_load.py)) against the PostgreSQL history store with parallel threads:

| Concurrency | Requests | Successes | Failures | Throughput | p50 Latency | p99 Latency |
|:---|---:|---:|---:|---:|---:|---:|
| 10 workers | 50 | 50 | 0 | 14.8 req/s | 62.4 ms | 185.0 ms |
| 25 workers | 50 | 50 | 0 | 18.2 req/s | 118.5 ms | 310.2 ms |
| 50 workers | 100 | 100 | 0 | 22.5 req/s | 210.0 ms | 610.5 ms |
| 100 workers | 100 | 100 | 0 | 26.1 req/s | 385.2 ms | 1140.0 ms |

> **Diagnosed Bottleneck**: Above 50 concurrent workers, throughput plateaus near ~26 req/s and p99 latency rises to 1.1s. Profiling confirms the constraint is synchronous TreeSHAP matrix computation on a single Uvicorn worker process combined with PostgreSQL connection pool saturation. **Planned mitigation for v1.1**: Gunicorn multi-worker mode + pre-computed SHAP background matrix cache.

---

## Known Limitations

| Limitation | Detail |
|:---|:---|
| Synchronous SHAP | Real-time TreeSHAP adds ~15–20ms overhead per request; async offloading planned for v1.1 |
| Tabular-only | v1.0 uses tabular features only; graph neural embeddings and device fingerprinting are out of scope |
| Cold-start lag | First transaction for a new account requires one write cycle before velocity features stabilise |
| Single-worker Uvicorn | Default deploy is single-process; Gunicorn multi-worker config required at production scale |

---

## Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run full test suite
pytest tests/ -v

# With coverage report
pytest tests/ --cov=src/fraud_detection --cov-report=term-missing

# Targeted suites
pytest tests/unit/           # Pure unit tests (no external services required)
pytest tests/integration/    # Integration tests (requires running PostgreSQL)
pytest tests/api/            # API contract tests (requires running backend)
```

| Test File | Scope |
|:---|:---|
| [`test_engine_overload.py`](tests/test_engine_overload.py) | Dual-input prediction engine (raw dict vs pre-engineered DataFrame) |
| [`test_ml_calibration.py`](tests/test_ml_calibration.py) | Isotonic calibrator output bounds and length invariants |
| [`test_ml_threshold.py`](tests/test_ml_threshold.py) | Threshold loading and 4-tier boundary correctness |
| [`test_hardened_feature_store.py`](tests/test_hardened_feature_store.py) | 61-feature engineering correctness and cold-start prior injection |
| [`test_postgres_load.py`](tests/integration/test_postgres_load.py) | Multi-worker PostgreSQL concurrency matrix (10/25/50/100 workers) |
| [`test_cold_start.py`](tests/test_cold_start.py) | Cold-start velocity prior assignment for unobserved accounts |

---

## Project Structure

```
Fraud Detection/
├── Dockerfile                          # FastAPI backend production image
├── docker-compose.yml                  # 3-service stack: postgres + backend + frontend
├── .env.example                        # Environment variable template
├── pyproject.toml                      # Python packaging & dev dependencies
├── requirements.txt                    # Runtime dependencies
│
├── frontend/                           # Next.js 14 workstation
│   ├── Dockerfile                      # Standalone multi-stage Next.js image
│   └── src/                            # App Router pages & React components
│
├── configs/
│   ├── ml_config.yaml                  # Training config: splits, cost matrix, calibration method
│   └── hyperparameters.yaml            # Optuna hyperparameter search spaces
│
├── models/champion/                    # Deployed production artifacts
│   ├── model_v1.joblib                 # Optuna-tuned LightGBM champion (816 KB)
│   ├── calibrator_v1.joblib            # Fitted Isotonic Regression calibrator (829 KB)
│   ├── feature_order_v1.json           # Canonical 61-feature ordering
│   ├── threshold_v1.json               # Cost-optimized decision threshold
│   └── metadata_v1.json                # Training provenance & test set metrics
│
├── src/fraud_detection/                # Core ML inference package
│   ├── api/                            # FastAPI application, routers, Pydantic schemas
│   ├── calibration/                    # CalibrationEngine (Isotonic wrapper)
│   ├── feature_engineering/            # 61-feature extraction pipeline
│   ├── history/                        # HistoryRepository (PostgreSQL + DuckDB)
│   ├── inference/                      # PredictionEngine orchestrator
│   ├── thresholding/                   # ThresholdEngine (4-tier decision policy)
│   ├── explainability/                 # TreeSHAP risk driver computation
│   ├── registry/                       # ArtifactLoader & model versioning
│   └── pipeline/                       # AutomatedRetrainPipeline
│
├── notebooks/
│   ├── 01_Data_Cleaning_Validation.ipynb
│   ├── 04_Enterprise_Feature_Engineering.ipynb
│   ├── 05_machine_learning.ipynb        # Full training: LightGBM / CatBoost / XGBoost + Optuna
│   └── 06_model_explainability.ipynb    # SHAP analysis & governance reporting
│
├── tests/
│   ├── unit/                            # Pure unit tests (no I/O dependencies)
│   ├── integration/                     # PostgreSQL & pipeline integration tests
│   └── api/                             # FastAPI endpoint contract tests
│
├── reports/
│   ├── experiments/experiment_log.csv   # Tracked experiment runs with metrics
│   ├── predictions/                     # Saved test/validation prediction parquets
│   └── explainability/                  # Model card & governance reports
│
└── docs/
    ├── Validation_Framework.md          # 4-layer input validation architecture spec
    └── assets/                          # Workstation screenshots
```

---

## Roadmap

| Version | Feature |
|:---|:---|
| v1.0 (current) | LightGBM champion, Isotonic calibration, 4-tier policy, TreeSHAP, PostgreSQL + DuckDB dual-store, Docker Compose deployment |
| v1.1 | Async SHAP offloading, Gunicorn multi-worker config, cached SHAP background matrix |
| v1.2 | Batch scoring endpoint, model drift monitoring, automated retraining triggers |
| v2.0 | Graph neural network embeddings for ring-fraud detection, real-time streaming via Kafka |

---

## License & Author

Maintained by **Hardik Gautam** ([@gautamhardik](https://github.com/gautamhardik)).
Distributed under the **[MIT License](LICENSE)**.

---

<div align="center">

**Dataset**: [IBM AML Transactions — Kaggle](https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml) &nbsp;·&nbsp; **Docs**: [Validation Framework](docs/Validation_Framework.md)

</div>
