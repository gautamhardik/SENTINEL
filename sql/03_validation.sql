-- 03_validation.sql: Data Warehouse QA, Referential Integrity, & Data Quality Scorecard Queries
-- Author: Hardik Gautam | Enterprise Integrity Verification

-- 1. Table Row Reconciliation Count
SELECT 'fact_transactions' AS table_name, COUNT(*) AS row_count FROM fact_transactions
UNION ALL
SELECT 'dim_time', COUNT(*) FROM dim_time
UNION ALL
SELECT 'dim_bank', COUNT(*) FROM dim_bank
UNION ALL
SELECT 'dim_account', COUNT(*) FROM dim_account
UNION ALL
SELECT 'dim_currency', COUNT(*) FROM dim_currency
UNION ALL
SELECT 'dim_payment_format', COUNT(*) FROM dim_payment_format;

-- 2. Foreign Key Referential Integrity Check (Orphan Detection)
SELECT 
    COUNT(*) AS orphan_fact_records
FROM fact_transactions f
LEFT JOIN dim_time t ON f.time_key = t.time_key
LEFT JOIN dim_bank fb ON f.from_bank_key = fb.bank_key
LEFT JOIN dim_account fa ON f.from_account_key = fa.account_key
LEFT JOIN dim_payment_format pf ON f.payment_format_key = pf.payment_format_key
WHERE t.time_key IS NULL OR fb.bank_key IS NULL OR fa.account_key IS NULL OR pf.payment_format_key IS NULL;

-- 3. Business Rule Validation: Invalid Negative Amounts
SELECT COUNT(*) AS invalid_negative_amount_count
FROM fact_transactions
WHERE amount_paid < 0 OR amount_received < 0;

-- 4. Enterprise Data Quality Scorecard Calculation
SELECT 
    COUNT(*) AS total_records,
    ROUND((1.0 - (SUM(CASE WHEN amount_paid IS NULL THEN 1.0 ELSE 0.0 END) / COUNT(*))) * 100.0, 2) AS completeness_score_pct,
    ROUND((1.0 - (SUM(CASE WHEN amount_paid < 0 THEN 1.0 ELSE 0.0 END) / COUNT(*))) * 100.0, 2) AS validity_score_pct,
    ROUND((1.0 - ((COUNT(*) - COUNT(DISTINCT transaction_id)) * 1.0 / COUNT(*))) * 100.0, 2) AS uniqueness_score_pct
FROM fact_transactions;
