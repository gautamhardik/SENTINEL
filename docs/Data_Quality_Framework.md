# 🎯 Sentinel Risk Engine — Data Quality Governance Framework

---

## 1. Executive Overview

The **Sentinel Data Quality Governance Framework** defines the data hygiene rules, completeness thresholds, and aggregate monitoring policies that govern feature data ingested by the Sentinel Risk Engine.

---

## 2. Core Data Quality Dimensions

### 1. Completeness ($100\%$ Required)
All 11 raw payload fields must be non-null and correctly typed before feature extraction begins. Missing fields cause instant HTTP 422 Unprocessable Entity rejection.

### 2. Consistency ($100\%$ Required)
Cross-currency payment amounts must align with ISO exchange rates. Inbound/outbound currency spreads ($|\text{Paid} - \text{Received}|$) are tracked as feature 3 (`amount_difference`).

### 3. Timeliness ($< 50$ms Requirement)
Real-time account velocity features (`sender_tx_count_1h`, `24h`, `7d`) are computed dynamically from PostgreSQL indexes to reflect exact historical account state.

---

## 3. Data Hygiene Thresholds

| Quality Metric | Governance Threshold | Monitoring Action |
|---|---|---|
| **Payload Null Rate** | Strict $0.0\%$ | Immediate HTTP 422 Rejection |
| **Outlier Threshold** | $\$10,000.00$ | Set `is_amount_outlier = 1.0` |
| **Max Payload Size** | $1.0$ MB | Gateway Rate Limit |
| **Max Timestamp Skew** | $\pm 5$ minutes | Reject Future Timestamps |
