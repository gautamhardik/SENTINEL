-- 05_reporting_views.sql: Production Reusable Reporting Views for Dashboards & Downstream BI

-- 1. Daily Fraud Summary View
CREATE OR REPLACE VIEW vw_daily_fraud_summary AS
SELECT 
    t.full_timestamp::DATE AS transaction_date,
    COUNT(*) AS total_transactions,
    SUM(f.is_laundering) AS fraud_cases,
    ROUND((SUM(f.is_laundering)::FLOAT / COUNT(*)) * 100, 2) AS fraud_rate_pct,
    SUM(f.amount_paid) AS total_volume_paid,
    SUM(CASE WHEN f.is_laundering = 1 THEN f.amount_paid ELSE 0 END) AS total_fraud_volume
FROM fact_transactions f
JOIN dim_time t ON f.time_key = t.time_key
GROUP BY t.full_timestamp::DATE;

-- 2. Weekly Fraud Summary View
CREATE OR REPLACE VIEW vw_weekly_fraud_summary AS
SELECT 
    t.year,
    t.quarter,
    COUNT(*) AS total_transactions,
    SUM(f.is_laundering) AS fraud_cases,
    ROUND((SUM(f.is_laundering)::FLOAT / COUNT(*)) * 100, 2) AS fraud_rate_pct,
    SUM(f.amount_paid) AS total_volume
FROM fact_transactions f
JOIN dim_time t ON f.time_key = t.time_key
GROUP BY t.year, t.quarter;

-- 3. Monthly Fraud Summary View
CREATE OR REPLACE VIEW vw_monthly_fraud_summary AS
SELECT 
    t.year,
    t.month,
    t.month_name,
    COUNT(*) AS total_transactions,
    SUM(f.is_laundering) AS fraud_cases,
    ROUND((SUM(f.is_laundering)::FLOAT / COUNT(*)) * 100, 2) AS fraud_rate_pct,
    SUM(f.amount_paid) AS total_volume
FROM fact_transactions f
JOIN dim_time t ON f.time_key = t.time_key
GROUP BY t.year, t.month, t.month_name;

-- 4. Bank Risk Scorecard View
CREATE OR REPLACE VIEW vw_bank_risk AS
SELECT 
    b.bank_name,
    COUNT(f.transaction_key) AS total_processed_tx,
    SUM(f.is_laundering) AS total_fraud_tx,
    ROUND((SUM(f.is_laundering)::FLOAT / COUNT(f.transaction_key)) * 100, 2) AS bank_fraud_rate_pct,
    SUM(f.amount_paid) AS total_volume_usd
FROM dim_bank b
JOIN fact_transactions f ON b.bank_key = f.from_bank_key
GROUP BY b.bank_name;

-- 5. Account High-Risk Velocity View
CREATE OR REPLACE VIEW vw_account_risk AS
SELECT 
    a.account_number,
    COUNT(f.transaction_key) AS total_transactions,
    SUM(f.amount_paid) AS total_volume_paid,
    SUM(f.is_laundering) AS total_fraud_events,
    MAX(t.full_timestamp) AS last_activity_timestamp
FROM dim_account a
JOIN fact_transactions f ON a.account_key = f.from_account_key
JOIN dim_time t ON f.time_key = t.time_key
GROUP BY a.account_number;

-- 6. High Value Accounts Summary View
CREATE OR REPLACE VIEW vw_high_value_accounts AS
SELECT 
    a.account_number,
    COUNT(f.transaction_key) AS transaction_count,
    SUM(f.amount_paid) AS total_sent_volume,
    AVG(f.amount_paid) AS avg_sent_amount
FROM dim_account a
JOIN fact_transactions f ON a.account_key = f.from_account_key
GROUP BY a.account_number
HAVING SUM(f.amount_paid) > 100000;

-- 7. Payment Format Breakdown View
CREATE OR REPLACE VIEW vw_payment_summary AS
SELECT 
    pf.format_name AS payment_format,
    COUNT(f.transaction_key) AS transaction_count,
    SUM(f.is_laundering) AS fraud_count,
    ROUND((SUM(f.is_laundering)::FLOAT / COUNT(f.transaction_key)) * 100, 2) AS fraud_rate_pct,
    SUM(f.amount_paid) AS total_volume
FROM dim_payment_format pf
JOIN fact_transactions f ON pf.payment_format_key = f.payment_format_key
GROUP BY pf.format_name;

-- 8. Bank Payment Format Risk Matrix View
CREATE OR REPLACE VIEW vw_bank_payment_risk AS
SELECT 
    b.bank_name,
    pf.format_name AS payment_format,
    COUNT(f.transaction_key) AS transaction_count,
    SUM(f.is_laundering) AS fraud_count
FROM dim_bank b
JOIN fact_transactions f ON b.bank_key = f.from_bank_key
JOIN dim_payment_format pf ON f.payment_format_key = pf.payment_format_key
GROUP BY b.bank_name, pf.format_name;

-- 9. Currency Flow Summary View
CREATE OR REPLACE VIEW vw_currency_summary AS
SELECT 
    c.currency_code,
    COUNT(f.transaction_key) AS transaction_count,
    SUM(f.is_laundering) AS fraud_count,
    SUM(f.amount_paid) AS total_volume
FROM dim_currency c
JOIN fact_transactions f ON c.currency_key = f.payment_currency_key
GROUP BY c.currency_code;

-- 10. Daily Currency Flow Trend View
CREATE OR REPLACE VIEW vw_daily_currency_flow AS
SELECT 
    t.full_timestamp::DATE AS transaction_date,
    c.currency_code,
    COUNT(f.transaction_key) AS transaction_count,
    SUM(f.amount_paid) AS daily_volume
FROM fact_transactions f
JOIN dim_time t ON f.time_key = t.time_key
JOIN dim_currency c ON f.payment_currency_key = c.currency_key
GROUP BY t.full_timestamp::DATE, c.currency_code;

-- 11. Hourly Fraud Activity View
CREATE OR REPLACE VIEW vw_hourly_activity AS
SELECT 
    t.hour,
    COUNT(*) AS total_transactions,
    SUM(f.is_laundering) AS fraud_count,
    ROUND((SUM(f.is_laundering)::FLOAT / COUNT(*)) * 100, 2) AS fraud_rate_pct
FROM fact_transactions f
JOIN dim_time t ON f.time_key = t.time_key
GROUP BY t.hour;

-- 12. High-Value Fraud Hotspots View
CREATE OR REPLACE VIEW vw_fraud_hotspots AS
SELECT 
    f.transaction_id,
    t.full_timestamp,
    fa.account_number AS sender_account,
    ta.account_number AS receiver_account,
    f.amount_paid,
    pf.format_name AS payment_format
FROM fact_transactions f
JOIN dim_time t ON f.time_key = t.time_key
JOIN dim_account fa ON f.from_account_key = fa.account_key
JOIN dim_account ta ON f.to_account_key = ta.account_key
JOIN dim_payment_format pf ON f.payment_format_key = pf.payment_format_key
WHERE f.is_laundering = 1;
