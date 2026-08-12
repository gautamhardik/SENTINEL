-- 04_business_analytics.sql: Enterprise Fraud Analytics & Advanced SQL Intelligence
-- Comprehensive 45 Analytical Query Showcase organized into 6 Enterprise Pillars.

-- ============================================================================
-- PILLAR 1: EXECUTIVE KPIS & SUMMARY METRICS (Queries 1-7)
-- ============================================================================

-- Q1: Core Transaction & Fraud Volume Totals
SELECT 
    COUNT(*) AS total_transactions,
    SUM(is_laundering) AS fraud_transactions,
    ROUND((SUM(is_laundering)::FLOAT / COUNT(*)) * 100, 2) AS fraud_rate_pct,
    SUM(amount_paid) AS total_volume_paid,
    SUM(CASE WHEN is_laundering = 1 THEN amount_paid ELSE 0 END) AS total_fraud_volume,
    ROUND((SUM(CASE WHEN is_laundering = 1 THEN amount_paid ELSE 0 END)::FLOAT / MAX(amount_paid)) * 100, 2) AS fraud_loss_pct
FROM fact_transactions;

-- Q2: Average, Median & Extremes
SELECT 
    ROUND(AVG(amount_paid), 2) AS avg_transaction_value,
    ROUND(AVG(CASE WHEN is_laundering = 1 THEN amount_paid ELSE NULL END), 2) AS avg_fraud_value,
    MAX(CASE WHEN is_laundering = 1 THEN amount_paid ELSE 0 END) AS max_fraud_amount,
    MIN(amount_paid) AS min_transaction_amount
FROM fact_transactions;

-- Q3: Distinct Entity Counts
SELECT 
    COUNT(DISTINCT from_account_key) AS unique_senders,
    COUNT(DISTINCT to_account_key) AS unique_receivers,
    COUNT(DISTINCT from_bank_key) AS unique_banks,
    COUNT(DISTINCT payment_currency_key) AS unique_currencies
FROM fact_transactions;

-- Q4: Daily Average Volume SLA
SELECT 
    COUNT(DISTINCT t.full_timestamp::DATE) AS total_operating_days,
    ROUND(COUNT(*)::FLOAT / COUNT(DISTINCT t.full_timestamp::DATE), 2) AS avg_daily_tx_count,
    ROUND(SUM(amount_paid)::FLOAT / COUNT(DISTINCT t.full_timestamp::DATE), 2) AS avg_daily_volume
FROM fact_transactions f
JOIN dim_time t ON f.time_key = t.time_key;

-- Q5: Top 5 Highest Fraud Volume Days
SELECT 
    t.full_timestamp::DATE AS transaction_date,
    COUNT(*) AS total_tx,
    SUM(f.is_laundering) AS fraud_tx,
    SUM(f.amount_paid) AS total_volume
FROM fact_transactions f
JOIN dim_time t ON f.time_key = t.time_key
GROUP BY t.full_timestamp::DATE
ORDER BY fraud_tx DESC
LIMIT 5;

-- Q6: Busiest Operating Days by Volume
SELECT 
    t.day_name,
    COUNT(*) AS transaction_count,
    SUM(f.amount_paid) AS total_volume
FROM fact_transactions f
JOIN dim_time t ON f.time_key = t.time_key
GROUP BY t.day_name
ORDER BY total_volume DESC;

-- Q7: Fraud Distribution by Weekday vs Weekend
SELECT 
    t.is_weekend,
    COUNT(*) AS transaction_count,
    SUM(f.is_laundering) AS fraud_count,
    ROUND((SUM(f.is_laundering)::FLOAT / COUNT(*)) * 100, 2) AS fraud_rate_pct
FROM fact_transactions f
JOIN dim_time t ON f.time_key = t.time_key
GROUP BY t.is_weekend;

-- ============================================================================
-- PILLAR 2: TEMPORAL & HOURLY TREND ANALYTICS (Queries 8-14)
-- ============================================================================

-- Q8: Daily Fraud Trend
SELECT 
    t.full_timestamp::DATE AS transaction_date,
    COUNT(*) AS total_transactions,
    SUM(f.is_laundering) AS fraud_cases,
    ROUND((SUM(f.is_laundering)::FLOAT / COUNT(*)) * 100, 2) AS daily_fraud_rate_pct,
    SUM(f.amount_paid) AS total_daily_volume
FROM fact_transactions f
JOIN dim_time t ON f.time_key = t.time_key
GROUP BY t.full_timestamp::DATE
ORDER BY transaction_date;

-- Q9: Hourly Fraud Peak Pattern
SELECT 
    t.hour,
    COUNT(*) AS transaction_count,
    SUM(f.is_laundering) AS fraud_count,
    ROUND((SUM(f.is_laundering)::FLOAT / COUNT(*)) * 100, 2) AS hourly_fraud_rate_pct,
    SUM(f.amount_paid) AS total_hourly_volume
FROM fact_transactions f
JOIN dim_time t ON f.time_key = t.time_key
GROUP BY t.hour
ORDER BY t.hour;

-- Q10: Monthly Fraud Aggregations
SELECT 
    t.year,
    t.month,
    t.month_name,
    COUNT(*) AS monthly_tx_count,
    SUM(f.is_laundering) AS monthly_fraud_count,
    SUM(f.amount_paid) AS monthly_volume
FROM fact_transactions f
JOIN dim_time t ON f.time_key = t.time_key
GROUP BY t.year, t.month, t.month_name
ORDER BY t.year, t.month;

-- Q11: Weekly Fraud Aggregations
SELECT 
    t.year,
    t.quarter,
    COUNT(*) AS tx_count,
    SUM(f.is_laundering) AS fraud_count,
    SUM(f.amount_paid) AS volume
FROM fact_transactions f
JOIN dim_time t ON f.time_key = t.time_key
GROUP BY t.year, t.quarter
ORDER BY t.year, t.quarter;

-- Q12: Night-time Off-Hour Fraud Exposure (Hours 00-05)
SELECT 
    COUNT(*) AS night_tx_count,
    SUM(f.is_laundering) AS night_fraud_count,
    ROUND((SUM(f.is_laundering)::FLOAT / COUNT(*)) * 100, 2) AS night_fraud_rate_pct
FROM fact_transactions f
JOIN dim_time t ON f.time_key = t.time_key
WHERE t.hour BETWEEN 0 AND 5;

-- Q13: Daytime Business Hour Exposure (Hours 09-17)
SELECT 
    COUNT(*) AS day_tx_count,
    SUM(f.is_laundering) AS day_fraud_count,
    ROUND((SUM(f.is_laundering)::FLOAT / COUNT(*)) * 100, 2) AS day_fraud_rate_pct
FROM fact_transactions f
JOIN dim_time t ON f.time_key = t.time_key
WHERE t.hour BETWEEN 9 AND 17;

-- Q14: Minute-Level Fraud Distribution
SELECT 
    t.minute,
    COUNT(*) AS transaction_count,
    SUM(f.is_laundering) AS fraud_count
FROM fact_transactions f
JOIN dim_time t ON f.time_key = t.time_key
GROUP BY t.minute
ORDER BY t.minute;

-- ============================================================================
-- PILLAR 3: CUSTOMER & ACCOUNT RISK INTELLIGENCE (Queries 15-22)
-- ============================================================================

-- Q15: Top 20 Risky Sender Accounts
SELECT 
    fa.account_number AS sender_account,
    COUNT(f.transaction_key) AS total_sent_tx,
    SUM(f.is_laundering) AS fraud_events,
    SUM(f.amount_paid) AS total_sent_volume
FROM fact_transactions f
JOIN dim_account fa ON f.from_account_key = fa.account_key
GROUP BY fa.account_number
ORDER BY fraud_events DESC, total_sent_volume DESC
LIMIT 20;

-- Q16: Top 20 Risky Receiver Accounts
SELECT 
    ta.account_number AS receiver_account,
    COUNT(f.transaction_key) AS total_received_tx,
    SUM(f.is_laundering) AS fraud_events,
    SUM(f.amount_received) AS total_received_volume
FROM fact_transactions f
JOIN dim_account ta ON f.to_account_key = ta.account_key
GROUP BY ta.account_number
ORDER BY fraud_events DESC, total_received_volume DESC
LIMIT 20;

-- Q17: Accounts with Highest Average Transfer Size
SELECT 
    fa.account_number,
    COUNT(f.transaction_key) AS tx_count,
    ROUND(AVG(f.amount_paid), 2) AS avg_transfer_size
FROM fact_transactions f
JOIN dim_account fa ON f.from_account_key = fa.account_key
GROUP BY fa.account_number
HAVING COUNT(f.transaction_key) >= 2
ORDER BY avg_transfer_size DESC
LIMIT 15;

-- Q18: Repeat Fraud Offenders (Accounts with Multiple Laundering Flags)
SELECT 
    fa.account_number,
    SUM(f.is_laundering) AS fraud_count,
    SUM(f.amount_paid) AS total_laundering_volume
FROM fact_transactions f
JOIN dim_account fa ON f.from_account_key = fa.account_key
WHERE f.is_laundering = 1
GROUP BY fa.account_number
HAVING SUM(f.is_laundering) > 1
ORDER BY fraud_count DESC;

-- Q19: Single-Transaction High Value Risk
SELECT 
    f.transaction_id,
    fa.account_number,
    f.amount_paid
FROM fact_transactions f
JOIN dim_account fa ON f.from_account_key = fa.account_key
WHERE f.amount_paid > 500000;

-- Q20: High Volume Legitimate Accounts (Benchmark Comparison)
SELECT 
    fa.account_number,
    COUNT(f.transaction_key) AS total_tx,
    SUM(f.amount_paid) AS total_volume
FROM fact_transactions f
JOIN dim_account fa ON f.from_account_key = fa.account_key
WHERE f.is_laundering = 0
GROUP BY fa.account_number
ORDER BY total_volume DESC
LIMIT 10;

-- Q21: Sender Concentration Index (Accounts Sending > 1% of Total Volume)
SELECT 
    fa.account_number,
    SUM(f.amount_paid) AS customer_volume,
    ROUND((SUM(f.amount_paid)::FLOAT / (SELECT SUM(amount_paid) FROM fact_transactions)) * 100, 2) AS volume_share_pct
FROM fact_transactions f
JOIN dim_account fa ON f.from_account_key = fa.account_key
GROUP BY fa.account_number
HAVING (SUM(f.amount_paid)::FLOAT / (SELECT SUM(amount_paid) FROM fact_transactions)) * 100 > 1.0;

-- Q22: Active Account Diversity Check
SELECT 
    COUNT(DISTINCT from_account_key) AS active_senders,
    COUNT(DISTINCT to_account_key) AS active_receivers
FROM fact_transactions;

-- ============================================================================
-- PILLAR 4: BANK, CURRENCY & PAYMENT FORMAT INTELLIGENCE (Queries 23-30)
-- ============================================================================

-- Q23: Sender Bank Risk Scorecard
SELECT 
    b.bank_name,
    COUNT(f.transaction_key) AS total_processed_tx,
    SUM(f.is_laundering) AS total_fraud_tx,
    ROUND((SUM(f.is_laundering)::FLOAT / COUNT(f.transaction_key)) * 100, 2) AS bank_fraud_rate_pct,
    SUM(f.amount_paid) AS total_volume
FROM dim_bank b
JOIN fact_transactions f ON b.bank_key = f.from_bank_key
GROUP BY b.bank_name
ORDER BY total_fraud_tx DESC;

-- Q24: Sender Bank vs Receiver Bank Matrix Breakdown
SELECT 
    fb.bank_name AS sender_bank,
    tb.bank_name AS receiver_bank,
    COUNT(*) AS total_transfers,
    SUM(f.is_laundering) AS fraud_transfers
FROM fact_transactions f
JOIN dim_bank fb ON f.from_bank_key = fb.bank_key
JOIN dim_bank tb ON f.to_bank_key = tb.bank_key
GROUP BY fb.bank_name, tb.bank_name
ORDER BY fraud_transfers DESC
LIMIT 15;

-- Q25: Cross-Bank Transfer Fraud Percentage
SELECT 
    CASE WHEN f.from_bank_key = f.to_bank_key THEN 'Intra-Bank' ELSE 'Inter-Bank' END AS transfer_type,
    COUNT(*) AS total_tx,
    SUM(f.is_laundering) AS fraud_tx,
    ROUND((SUM(f.is_laundering)::FLOAT / COUNT(*)) * 100, 2) AS fraud_rate_pct
FROM fact_transactions f
GROUP BY CASE WHEN f.from_bank_key = f.to_bank_key THEN 'Intra-Bank' ELSE 'Inter-Bank' END;

-- Q26: Payment Format Risk Ranking
SELECT 
    pf.format_name AS payment_format,
    COUNT(f.transaction_key) AS transaction_count,
    SUM(f.is_laundering) AS fraud_count,
    ROUND((SUM(f.is_laundering)::FLOAT / COUNT(f.transaction_key)) * 100, 2) AS format_fraud_rate_pct,
    SUM(f.amount_paid) AS total_volume
FROM dim_payment_format pf
JOIN fact_transactions f ON pf.payment_format_key = f.payment_format_key
GROUP BY pf.format_name
ORDER BY fraud_count DESC;

-- Q27: Average Amount per Payment Type
SELECT 
    pf.format_name,
    ROUND(AVG(f.amount_paid), 2) AS avg_amount,
    ROUND(AVG(CASE WHEN f.is_laundering = 1 THEN f.amount_paid ELSE NULL END), 2) AS avg_fraud_amount
FROM dim_payment_format pf
JOIN fact_transactions f ON pf.payment_format_key = f.payment_format_key
GROUP BY pf.format_name;

-- Q28: Currency Flow Distribution
SELECT 
    c.currency_code,
    COUNT(f.transaction_key) AS transaction_count,
    SUM(f.is_laundering) AS fraud_count,
    SUM(f.amount_paid) AS total_volume
FROM dim_currency c
JOIN fact_transactions f ON c.currency_key = f.payment_currency_key
GROUP BY c.currency_code
ORDER BY total_volume DESC;

-- Q29: Cross-Currency FX Exchange Fraud
SELECT 
    pc.currency_code AS paying_currency,
    rc.currency_code AS receiving_currency,
    COUNT(*) AS total_fx_tx,
    SUM(f.is_laundering) AS fraud_fx_tx
FROM fact_transactions f
JOIN dim_currency pc ON f.payment_currency_key = pc.currency_key
JOIN dim_currency rc ON f.receiving_currency_key = rc.currency_key
GROUP BY pc.currency_code, rc.currency_code
ORDER BY fraud_fx_tx DESC;

-- Q30: Bank Market Share by Volume
SELECT 
    b.bank_name,
    SUM(f.amount_paid) AS processed_volume,
    ROUND((SUM(f.amount_paid)::FLOAT / (SELECT SUM(amount_paid) FROM fact_transactions)) * 100, 2) AS market_share_pct
FROM dim_bank b
JOIN fact_transactions f ON b.bank_key = f.from_bank_key
GROUP BY b.bank_name
ORDER BY processed_volume DESC;

-- ============================================================================
-- PILLAR 5: INVESTIGATION PATTERNS & ANOMALY DETECTION (Queries 31-37)
-- ============================================================================

-- Q31: One-to-Many Transfer Pattern (One Sender to Multiple Receivers)
SELECT 
    fa.account_number AS sender_account,
    COUNT(DISTINCT f.to_account_key) AS distinct_receivers,
    COUNT(f.transaction_key) AS total_tx,
    SUM(f.is_laundering) AS fraud_events
FROM fact_transactions f
JOIN dim_account fa ON f.from_account_key = fa.account_key
GROUP BY fa.account_number
HAVING COUNT(DISTINCT f.to_account_key) > 3
ORDER BY distinct_receivers DESC;

-- Q32: Many-to-One Transfer Pattern (Multiple Senders to One Receiver)
SELECT 
    ta.account_number AS receiver_account,
    COUNT(DISTINCT f.from_account_key) AS distinct_senders,
    COUNT(f.transaction_key) AS total_tx,
    SUM(f.is_laundering) AS fraud_events
FROM fact_transactions f
JOIN dim_account ta ON f.to_account_key = ta.account_key
GROUP BY ta.account_number
HAVING COUNT(DISTINCT f.from_account_key) > 3
ORDER BY distinct_senders DESC;

-- Q33: Top 10 High-Value Fraud Transactions
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
WHERE f.is_laundering = 1
ORDER BY f.amount_paid DESC
LIMIT 10;

-- Q34: Rapid Repeat Transfer Detection
SELECT 
    fa.account_number AS sender_account,
    COUNT(f.transaction_key) AS transaction_count,
    SUM(f.amount_paid) AS total_sent_volume,
    SUM(f.is_laundering) AS fraud_events
FROM fact_transactions f
JOIN dim_account fa ON f.from_account_key = fa.account_key
GROUP BY fa.account_number
HAVING COUNT(f.transaction_key) > 3
ORDER BY transaction_count DESC;

-- Q35: Self-Loop Transfers (Same Sender and Receiver Account)
SELECT 
    f.transaction_id,
    fa.account_number,
    f.amount_paid
FROM fact_transactions f
JOIN dim_account fa ON f.from_account_key = fa.account_key
WHERE f.from_account_key = f.to_account_key;

-- Q36: Structuring Anomaly Detection (Amounts just under $10,000 threshold)
SELECT 
    f.transaction_id,
    fa.account_number,
    f.amount_paid,
    f.is_laundering
FROM fact_transactions f
JOIN dim_account fa ON f.from_account_key = fa.account_key
WHERE f.amount_paid BETWEEN 9000 AND 9999;

-- Q37: Extreme Monetary Outlier Flag Audit
SELECT 
    COUNT(*) AS outlier_flagged_tx,
    SUM(is_laundering) AS outlier_fraud_cases,
    ROUND((SUM(is_laundering)::FLOAT / COUNT(*)) * 100, 2) AS outlier_fraud_rate_pct
FROM fact_transactions
WHERE is_amount_outlier = 1;

-- ============================================================================
-- PILLAR 6: ADVANCED WINDOW FUNCTIONS & ANALYTICAL RANKINGS (Queries 38-45)
-- ============================================================================

-- Q38: RANK() and DENSE_RANK() of Transaction Amounts per Customer
SELECT 
    f.transaction_id,
    fa.account_number AS sender_account,
    f.amount_paid,
    ROW_NUMBER() OVER (PARTITION BY f.from_account_key ORDER BY f.amount_paid DESC) AS row_num,
    RANK() OVER (PARTITION BY f.from_account_key ORDER BY f.amount_paid DESC) AS rank_num,
    DENSE_RANK() OVER (PARTITION BY f.from_account_key ORDER BY f.amount_paid DESC) AS dense_rank_num
FROM fact_transactions f
JOIN dim_account fa ON f.from_account_key = fa.account_key
LIMIT 20;

-- Q39: LAG() and LEAD() Previous / Next Transaction Amount Comparison
SELECT 
    f.transaction_id,
    fa.account_number,
    f.amount_paid,
    LAG(f.amount_paid, 1) OVER (PARTITION BY f.from_account_key ORDER BY f.time_key) AS previous_amount,
    LEAD(f.amount_paid, 1) OVER (PARTITION BY f.from_account_key ORDER BY f.time_key) AS next_amount
FROM fact_transactions f
JOIN dim_account fa ON f.from_account_key = fa.account_key
LIMIT 20;

-- Q40: NTILE(4) Quartile Partitioning of Transaction Amounts
SELECT 
    f.transaction_id,
    f.amount_paid,
    f.is_laundering,
    NTILE(4) OVER (ORDER BY f.amount_paid ASC) AS amount_quartile
FROM fact_transactions f
LIMIT 20;

-- Q41: PERCENT_RANK() & CUME_DIST() Cumulative Distribution
SELECT 
    f.transaction_id,
    f.amount_paid,
    PERCENT_RANK() OVER (ORDER BY f.amount_paid ASC) AS pct_rank,
    CUME_DIST() OVER (ORDER BY f.amount_paid ASC) AS cume_dist_val
FROM fact_transactions f
LIMIT 20;

-- Q42: Running Cumulative Volume per Customer Account
SELECT 
    f.transaction_id,
    fa.account_number,
    f.amount_paid,
    SUM(f.amount_paid) OVER (PARTITION BY f.from_account_key ORDER BY f.time_key) AS customer_running_volume
FROM fact_transactions f
JOIN dim_account fa ON f.from_account_key = fa.account_key
LIMIT 20;

-- Q43: Moving 3-Transaction Average Amount
SELECT 
    f.transaction_id,
    fa.account_number,
    f.amount_paid,
    AVG(f.amount_paid) OVER (
        PARTITION BY f.from_account_key 
        ORDER BY f.time_key 
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS moving_avg_3tx
FROM fact_transactions f
JOIN dim_account fa ON f.from_account_key = fa.account_key
LIMIT 20;

-- Q44: Running Fraud Rate per Customer Account
SELECT 
    f.transaction_id,
    fa.account_number,
    f.is_laundering,
    AVG(f.is_laundering) OVER (
        PARTITION BY f.from_account_key 
        ORDER BY f.time_key
    ) AS running_fraud_rate
FROM fact_transactions f
JOIN dim_account fa ON f.from_account_key = fa.account_key
LIMIT 20;

-- Q45: Rolling Daily Fraud Volume Trend
SELECT 
    t.full_timestamp::DATE AS transaction_date,
    SUM(f.is_laundering) AS daily_fraud_count,
    SUM(SUM(f.is_laundering)) OVER (
        ORDER BY t.full_timestamp::DATE 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS rolling_7day_fraud_count
FROM fact_transactions f
JOIN dim_time t ON f.time_key = t.time_key
GROUP BY t.full_timestamp::DATE
ORDER BY transaction_date;
