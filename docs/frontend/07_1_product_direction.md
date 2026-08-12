# Phase 7.1 — Product Direction & UX Discovery Master Audit

---

## 1. PRODUCT DEFINITION

**Sentinel Risk Engine** is a precision, single-transaction financial fraud screening tool. It allows a risk reviewer to input 11 raw transaction parameters, execute real-time ML model inference via a hardened FastAPI serving layer, and receive an instant, calibrated fraud risk assessment paired with plain-language explainability drivers and explicit recommended actions.

It is **NOT** a dashboard, analytics portal, BI platform, cybersecurity command center, or generic AI demo. It is a focused, single-purpose financial screening instrument.

---

## 2. PRODUCT PURPOSE

**Sentinel Risk Engine** solves one critical problem:

> *"Evaluating whether a single financial transaction carries fraud risk, explaining why the system flagged or approved it, and providing a clear operational recommendation without forcing the user to interpret raw machine-learning output."*

It bridges the gap between sophisticated backend ML infrastructure (61 features, Optuna-tuned LightGBM, Isotonic calibration, SHAP feature importance) and operational decision-making.

---

## 3. PRIMARY USER

### The Risk Operations Reviewer
- **Role**: Risk Reviewer / Compliance Operations Analyst.
- **Context**: Responsible for evaluating suspicious, high-value, or flagged transactions passed from payment gateways, core banking platforms, or wire systems.
- **Goal**: Make a fast, confident, and defensible decision (**Approve**, **Monitor**, **Hold for Investigation**, or **Decline**) on a single transaction.
- **What they care about**: Clear decision guidance, calibrated risk score, top underlying risk drivers, transaction verification details.
- **What they DO NOT care about**: 61-feature vector definitions, hyperparameter tuning logs, SQL query execution plans, raw SHAP math arrays, or global model metrics.

---

## 4. USER GOAL

The user wants to accomplish a single task cleanly and efficiently:

1. **Submit** 11 raw transaction fields (`transaction_id`, `Timestamp`, `From_Account`, `To_Account`, `From_Bank`, `To_Bank`, `Amount_Paid`, `Amount_Received`, `Payment_Format`, `Payment_Currency`, `Receiving_Currency`).
2. **Obtain** a definitive fraud probability score, risk decision category, and recommended action.
3. **Understand** the key behavioral or amount-driven factors behind the score.
4. **Determine** next operational steps with zero ambiguity.

---

## 5. USER MENTAL MODEL

### User Mental Model (Desired)
```
[ Enter Transaction Parameters ] ➔ [ Analyze Risk ] ➔ [ Review Decision & Risk Drivers ] ➔ [ Take Action ]
```

### System Mental Model (Hidden Behind API)
```
[ Raw Transaction Payload ] ➔ [ Online Feature Store Lookup ] ➔ [ PostgreSQL State Aggr ] ➔ [ 61 Feature Builders ] ➔ [ LightGBM Raw Prob ] ➔ [ Isotonic Calibration ] ➔ [ Threshold Engine ] ➔ [ SHAP TreeExplainer ] ➔ [ State Persist ]
```

The user must interact purely with the **User Mental Model**. The system's internal complexity remains concealed behind the `POST /api/v1/predict` API.

---

## 6. CORE USER JOURNEY

The user experience progresses sequentially through 4 distinct, focused operational states:

1. **State 1: Transaction Entry**: Clean, structured input form accepting the 11 raw fields with sensible defaults (e.g. current ISO timestamp, `USD`, `Wire` or `ACH`).
2. **State 2: Analyzing / Processing State**: Visual feedback showing active screening. Fast, intentional execution without fake artificial delays.
3. **State 3: Assessment Result**: Prominent risk badge (`APPROVED_LEGITIMATE`, `APPROVED_WITH_MONITORING`, `FLAGGED_FRAUD`, `FLAGGED_CRITICAL_FRAUD`), calibrated probability badge, recommended action, top risk drivers (SHAP explanations), and Markdown investigator decision summary card.
4. **State 4: Action / Next Step**: Immediate option to screen another transaction or copy decision report for audit records.

---

## 7. MVP SCOPE

### What MUST Exist (In-Scope for Frontend)
- Single-page workflow focused entirely on 1-transaction screening.
- Strict 11-field raw input form (`transaction_id`, `Timestamp`, `From_Account`, `To_Account`, `From_Bank`, `To_Bank`, `Amount_Paid`, `Amount_Received`, `Payment_Format`, `Payment_Currency`, `Receiving_Currency`).
- Primary submission action trigger (*"Screen Transaction"*).
- Direct integration with `POST /api/v1/predict`.
- Risk Category Badge (`APPROVED_LEGITIMATE`, `APPROVED_WITH_MONITORING`, `FLAGGED_FRAUD`, `FLAGGED_CRITICAL_FRAUD`).
- Calibrated Fraud Probability display (percentage representation of `calibrated_probability`).
- Decision Threshold representation (`0.2556561085972851`).
- Recommended Action Card (`APPROVE`, `MONITOR`, `HOLD_FOR_MANUAL_INVESTIGATION`, `DECLINE_IMMEDIATELY`).
- Plain-language Risk Drivers (mapped directly from `explanation.top_risk_drivers`).
- Investigator Decision Card (rendered Markdown from `explanation.investigator_card`).
- Real error boundary handling for validation (HTTP 422) and server failures (HTTP 500/503).

---

## 8. OUT OF SCOPE

- ❌ Sidebar navigation / multi-tab layouts
- ❌ KPI dashboards (e.g. Total Screened, Total Fraud $, Approval Rate %)
- ❌ Fraud trend charts, velocity line graphs, or time-series plots
- ❌ Analytics grids, BI reports, or data export tables
- ❌ Fake historical transaction feeds or mock transaction lists
- ❌ Batch processing UI or CSV upload workflows
- ❌ User login, authentication, RBAC, or settings pages
- ❌ Model comparison, ROC/AUC curve views, or hyperparameter details
- ❌ Input fields for engineered features (`is_amount_outlier`, rolling stats, velocity counts, 61-feature vectors)
- ❌ Cybersecurity "dark hacker" or "neon cyberpunk" visual aesthetics

---

## 9. LOCKED PRODUCT DECISIONS

1. **Single-Page Form + Result Architecture**: The application consists strictly of a single screening view.
2. **11-Field Input Schema**: Frontend collects ONLY the 11 raw transaction parameters.
3. **Backend Outlier Ownership**: `is_amount_outlier` is completely hidden from the user interface.
4. **Primary Endpoint Contract**: Frontend communicates exclusively with `POST /api/v1/predict`.
5. **Zero Dashboard Artifacts**: No charts, sidebars, KPI grids, or trend widgets will be created.
6. **No Mock Data**: Every result displayed comes directly from the live FastAPI + LightGBM + Isotonic + SHAP backend.
