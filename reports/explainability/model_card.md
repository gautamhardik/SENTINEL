# 🛡️ Enterprise Model Card: Fraud Detection Champion Model

## 1. Model Overview & Identification
- **Model Name:** `catboost_Tuned`
- **Model Version:** `v16`
- **Registry Status:** `CHAMPION`
- **Creation Date:** 2026-08-05
- **Primary Objective:** High-precision real-time financial transaction fraud & money laundering detection.

## 2. Intended Use & Target Scope
- **Primary Users:** Fraud Investigation Teams, Risk Operations, Real-Time Gateway Engines.
- **Supported Environment:** Real-time transaction authorization pipeline & batch post-transaction monitoring.

## 3. Out-of-Scope & Prohibited Use
- ❌ Automated account termination or asset freezing without human analyst review.
- ❌ Credit risk scoring or loan underwriting evaluations.

## 4. Training Data & Preprocessing Pipeline
- **Dataset Size:** ~1.4M transactions (70% Train, 15% Validation, 15% Test).
- **Features:** 61 engineered transaction velocity, aggregation, and interaction features.
- **Preprocessing:** Median imputation, Standard Scaling on continuous features, One-Hot Encoding on categorical features.

## 5. Model Architecture & Hyperparameters
- **Base Framework:** CatBoost Classifier
- **Loss Function:** Logloss
- **Class Balancing:** `auto_class_weights='Balanced'`
- **Random Seed:** 42

## 6. Calibration Method & Rationale
- **Method:** Isotonic Regression fitted strictly on validation set predictions.
- **Impact:** Converts raw GBDT scores into well-calibrated posterior probabilities, ensuring that a predicted score of 0.80 corresponds to an actual 80% fraud risk.

## 7. Threshold Optimization & Business Rationale
- **Optimal Threshold:** `0.26`
- **Selection Criteria:** Minimizes total business cost loss ($15 FP operational cost vs. $500 FN fraud loss).

## 8. Production Performance Metrics (Test Set)
| Metric | Production Value | Enterprise Benchmark | Status |
| :--- | :---: | :---: | :---: |
| **PR-AUC** | **0.8486** | >= 0.75 | PASS |
| **ROC-AUC** | **0.9698** | >= 0.90 | PASS |
| **F1-Score** | **0.7646** | >= 0.70 | PASS |
| **Recall (Fraud Capture)** | **76.00%** | >= 70% | PASS |
| **Inference Latency** | **< 0.05 ms** | <= 10.0 ms | PASS |

## 9. Model Interpretability & Feature Importance
- **Primary Risk Drivers:** `is_amount_outlier`, `amount_paid`, `amount_received`.
- **Explainability Engine:** SHAP (SHapley Additive exPlanations) TreeExplainer integrated for global feature ranking and local transaction waterfall attributions.

## 10. Fairness, Bias & Ethical Considerations
- **Demographic Exclusion:** Zero demographic or geographic discriminatory attributes utilized.
- **Human-in-the-Loop:** High-risk predictions above threshold trigger manual analyst review queues before final blocking action.

## 11. Robustness & Sensitivity Profiling
- **Perturbation Stability:** Stable under +/- 10% feature noise with < 0.01 mean probability shift and 0 decision flips on top drivers.

## 12. Monitoring Recommendations & Drift Triggers
- **Drift Baseline:** `drift_reference.json`
- **Alert Criteria:** Retrain if monthly PR-AUC drops below `0.78` or PSI drift exceeds `0.25`.

## 13. Governance Approval & Audit Sign-Off
- **Model Developer:** Lead AI/ML Engineering Team
- **Approval Status:** ✅ APPROVED FOR PRODUCTION DEPLOYMENT
