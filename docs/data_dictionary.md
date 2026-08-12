# 📖 Sentinel Risk Engine — 61-Feature Data Dictionary

---

## 1. Executive Summary

This document serves as the authoritative data dictionary for the **Sentinel 61-Feature Vector**. Every transaction submitted to the API (`POST /api/v1/predict`) is mapped into these 61 standardized features in the exact ordering defined by `feature_order_v1.json`.

---

## 2. Complete 61-Feature Data Specification Table

| Index | Feature Key Name | Data Type | Value Range / Units | Source / Derivation Rule | Description |
|---:|---|---|---|---|---|
| **1** | `Amount_Paid` | Float64 | $[0.0, \infty)$ USD | Raw Payload Field | Outbound payment amount in USD equivalent. |
| **2** | `Amount_Received` | Float64 | $[0.0, \infty)$ USD | Raw Payload Field | Inbound settlement amount in receiving currency. |
| **3** | `amount_difference` | Float64 | $[0.0, \infty)$ USD | Calculated ($|\text{Paid} - \text{Received}|$) | Currency conversion delta or fee spread. |
| **4** | `amount_ratio` | Float64 | $[0.0, 100.0]$ ratio | Calculated ($\frac{\text{Received}}{\text{Paid} + 1e-6}$) | Settlement amount ratio. |
| **5** | `log_amount` | Float64 | $[0.0, 20.0]$ log scale | Calculated ($\ln(\text{Amount\_Paid} + 1.0)$) | Logarithmic scaling for high-value outliers. |
| **6** | `is_amount_outlier` | Float64 | $\{0.0, 1.0\}$ flag | Derived ($\text{Amount\_Paid} > 10000.0$) | High-value threshold indicator flag. |
| **7** | `same_bank_flag` | Float64 | $\{0.0, 1.0\}$ flag | Derived ($\text{From\_Bank} == \text{To\_Bank}$) | Internal intra-bank transfer flag. |
| **8** | `is_cross_currency` | Float64 | $\{0.0, 1.0\}$ flag | Derived ($\text{Pay\_Curr} \neq \text{Recv\_Curr}$) | International currency exchange flag. |
| **9** | `sender_tx_count_1h` | Float64 | $[0, \infty)$ count | Feature Store Velocity | Transactions sent by account in past hour. |
| **10** | `sender_tx_count_24h` | Float64 | $[0, \infty)$ count | Feature Store Velocity | Transactions sent by account in past 24 hours. |
| **11** | `sender_tx_count_7d` | Float64 | $[0, \infty)$ count | Feature Store Velocity | Transactions sent by account in past 7 days. |
| **12** | `receiver_tx_count_1h` | Float64 | $[0, \infty)$ count | Feature Store Velocity | Transactions received by account in past hour. |
| **13** | `receiver_tx_count_24h` | Float64 | $[0, \infty)$ count | Feature Store Velocity | Transactions received by account in past 24 hours. |
| **14** | `receiver_tx_count_7d` | Float64 | $[0, \infty)$ count | Feature Store Velocity | Transactions received by account in past 7 days. |
| **15** | `sender_amount_sum_24h` | Float64 | $[0.0, \infty)$ USD | Feature Store Aggregate | Total volume sent by account in past 24 hours. |
| **16** | `receiver_amount_sum_24h` | Float64 | $[0.0, \infty)$ USD | Feature Store Aggregate | Total volume received by account in past 24 hours. |
| **17** | `sender_amount_mean_24h` | Float64 | $[0.0, \infty)$ USD | Feature Store Aggregate | Mean payment size for sender in past 24 hours. |
| **18** | `sender_amount_std_24h` | Float64 | $[0.0, \infty)$ USD | Feature Store Aggregate | Standard deviation of payment size for sender. |
| **19** | `time_since_last_tx_sender` | Float64 | $[0.0, \infty)$ sec | Feature Store Velocity | Seconds elapsed since sender's last transfer. |
| **20** | `time_since_last_tx_receiver` | Float64 | $[0.0, \infty)$ sec | Feature Store Velocity | Seconds elapsed since receiver's last transfer. |
| **21–25** | `fmt_wire`, `fmt_ach`, `fmt_cheque`, `fmt_card`, `fmt_cash` | Float64 | $\{0.0, 1.0\}$ binary | One-Hot Encoding | Payment channel rail category indicators. |
| **26–30** | `pay_curr_usd`, `eur`, `gbp`, `cad`, `aud` | Float64 | $\{0.0, 1.0\}$ binary | One-Hot Encoding | Payment currency categorization indicators. |
| **31–35** | `recv_curr_usd`, `eur`, `gbp`, `cad`, `aud` | Float64 | $\{0.0, 1.0\}$ binary | One-Hot Encoding | Receiving currency categorization indicators. |
| **36–48** | Historical Bank Risk Profiles | Float64 | $[0.0, 1.0]$ ratio | Historical Prior Lookup | Bank-level baseline fraud rate profiles. |
| **49–54** | `hour_sin`, `hour_cos`, `day_sin`, `day_cos`, `is_weekend` | Float64 | $[-1.0, 1.0]$ cyclic | Trigonometric Encoding | Cyclic time of day and day of week indicators. |
| **55–61** | Cross Interaction Terms | Float64 | Variations | Vectorized Combination | Velocity and amount cross-interaction terms. |

---

## 3. Input Validation & Contract Guard Rules

- **Raw Payload**: The public REST API (`POST /api/v1/predict`) accepts **ONLY** the 11 raw transaction fields (`transaction_id`, `Timestamp`, `From_Account`, `To_Account`, `From_Bank`, `To_Bank`, `Amount_Paid`, `Amount_Received`, `Payment_Format`, `Payment_Currency`, `Receiving_Currency`).
- **Forbidden Inputs**: Engineered features, model probabilities, SHAP values, and decision thresholds MUST NOT be passed by the client.
- **Strict Derivation**: All 61 features are constructed server-side in real-time before model invocation.
