-- 02_views.sql: Production Analytical Views for BI & Dashboarding
-- Author: Hardik Gautam | Phase 2 Star Schema Business Views

CREATE OR REPLACE VIEW vw_daily_transactions AS
SELECT 
    t.full_timestamp::DATE AS transaction_date,
    COUNT(*) AS total_transactions,
    SUM(f.amount_paid) AS total_volume_paid,
    SUM(f.is_laundering) AS total_fraud_transactions,
    ROUND((SUM(f.is_laundering)::FLOAT / COUNT(*)) * 100, 2) AS daily_fraud_rate_pct
FROM fact_transactions f
JOIN dim_time t ON f.time_key = t.time_key
GROUP BY t.full_timestamp::DATE;

CREATE OR REPLACE VIEW vw_customer_summary AS
SELECT 
    a.account_number,
    COUNT(f.transaction_key) AS total_transactions_sent,
    SUM(f.amount_paid) AS total_volume_sent,
    SUM(f.is_laundering) AS total_fraud_events,
    MAX(t.full_timestamp) AS last_transaction_timestamp
FROM dim_account a
JOIN fact_transactions f ON a.account_key = f.from_account_key
JOIN dim_time t ON f.time_key = t.time_key
GROUP BY a.account_number;

CREATE OR REPLACE VIEW vw_fraud_overview AS
SELECT 
    f.transaction_id,
    t.full_timestamp,
    fa.account_number AS sender_account,
    ta.account_number AS receiver_account,
    fb.bank_name AS sender_bank,
    tb.bank_name AS receiver_bank,
    f.amount_paid,
    pf.format_name AS payment_format
FROM fact_transactions f
JOIN dim_time t ON f.time_key = t.time_key
JOIN dim_account fa ON f.from_account_key = fa.account_key
JOIN dim_account ta ON f.to_account_key = ta.account_key
JOIN dim_bank fb ON f.from_bank_key = fb.bank_key
JOIN dim_bank tb ON f.to_bank_key = tb.bank_key
JOIN dim_payment_format pf ON f.payment_format_key = pf.payment_format_key
WHERE f.is_laundering = 1;

CREATE OR REPLACE VIEW vw_bank_summary AS
SELECT 
    b.bank_name,
    COUNT(f.transaction_key) AS total_processed_transactions,
    SUM(f.amount_paid) AS total_processed_volume,
    SUM(f.is_laundering) AS total_fraud_cases,
    ROUND((SUM(f.is_laundering)::FLOAT / COUNT(f.transaction_key)) * 100, 2) AS bank_fraud_rate_pct
FROM dim_bank b
JOIN fact_transactions f ON b.bank_key = f.from_bank_key
GROUP BY b.bank_name;
