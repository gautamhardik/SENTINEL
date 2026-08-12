# 📖 Sentinel Risk Engine — SQL Analytics & Query Execution Guide

---

## 1. Executive Summary

This guide provides data analysts, compliance investigators, and ML engineers with a reference for executing SQL analytical queries against the **Sentinel Data Warehouse** and **PostgreSQL 15 Feature Store**.

---

## 2. Connecting to the Database

### Production PostgreSQL Container
```bash
docker exec -it sentinel-postgres psql -U sentinel_user -d fraud_detection
```

### Local DuckDB File Storage
```python
import duckdb
conn = duckdb.connect("data/warehouse.duckdb")
df = conn.execute("SELECT * FROM transaction_history LIMIT 10;").df()
```

---

## 3. High-Frequency Analytical Query Patterns

### Pattern A: Account Velocity Summary
```sql
SELECT 
    from_account AS account_id,
    COUNT(*) AS total_tx_24h,
    SUM(amount_paid) AS total_volume_usd,
    AVG(amount_paid) AS avg_tx_size
FROM transaction_history
WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
GROUP BY from_account
HAVING COUNT(*) > 5
ORDER BY total_volume_usd DESC;
```

### Pattern B: Fraud Flag Rate by Payment Rail
```sql
SELECT 
    payment_format,
    COUNT(*) AS total_transactions,
    SUM(is_laundering) AS fraud_cases,
    ROUND((SUM(is_laundering)::numeric / COUNT(*)) * 100, 2) AS fraud_rate_pct
FROM transaction_history
GROUP BY payment_format
ORDER BY fraud_rate_pct DESC;
```
