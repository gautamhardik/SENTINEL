# ⭐ Sentinel Risk Engine — Star Schema Dimensional Specification

---

## 1. Executive Overview

The **Sentinel Dimensional Model** organizes historical transactional data into a Star Schema optimized for OLAP analytics, BI reporting, and historical offline ML model training datasets.

---

## 2. Dimensional Model Architecture

```text
                               ┌───────────────────┐
                               │     dim_time      │
                               └─────────┬─────────┘
                                         │
                                         ▼
┌───────────────────┐          ┌───────────────────┐          ┌───────────────────┐
│     dim_bank      ├─────────►│ fact_transactions │◄─────────┤    dim_account    │
└───────────────────┘          └─────────▲─────────┘          └───────────────────┘
                                         │
                                         ├──────────────────┐
                                         │                  │
                               ┌─────────┴─────────┐ ┌──────┴──────────────┐
                               │   dim_currency    │ │ dim_payment_format  │
                               └───────────────────┘ └─────────────────────┘
```

---

## 3. Detailed Table Specifications

### Fact Table: `fact_transactions`
- **Primary Key**: `transaction_sk` (BigInt)
- **Surrogate Foreign Keys**: `time_key`, `from_account_key`, `to_account_key`, `from_bank_key`, `to_bank_key`, `payment_format_key`, `currency_key`
- **Degenerate Dimensions**: `transaction_id` (String)
- **Numeric Measures**: `amount_paid`, `amount_received`, `amount_difference`, `amount_ratio`, `log_amount`
- **Target Flag**: `is_laundering` (SmallInt binary flag: 1 = Fraud, 0 = Legitimate)

### Dimension Tables
1. **`dim_account`**: `account_key`, `account_id`, `creation_timestamp`, `account_type`, `risk_tier`.
2. **`dim_bank`**: `bank_key`, `bank_id`, `bank_name`, `country_code`, `routing_region`.
3. **`dim_time`**: `time_key`, `timestamp`, `year`, `quarter`, `month`, `day`, `hour`, `minute`, `day_of_week`, `is_weekend`.
4. **`dim_payment_format`**: `payment_format_key`, `format_name` (`Wire Transfer`, `ACH Outbound`, `Cheque`, `Credit Card`, `Cash Deposit`).
5. **`dim_currency`**: `currency_key`, `currency_code` (`USD`, `EUR`, `GBP`, `CAD`, `AUD`), `is_base_currency`.
