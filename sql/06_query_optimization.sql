-- 06_query_optimization.sql: Production SQL Query Optimization, Indexing & Plan Benchmarks

-- ============================================================================
-- SECTION 1: B-TREE & COMPOSITE INDEX CREATION DDL
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_fact_is_laundering ON fact_transactions(is_laundering);
CREATE INDEX IF NOT EXISTS idx_fact_time_key ON fact_transactions(time_key);
CREATE INDEX IF NOT EXISTS idx_fact_from_account ON fact_transactions(from_account_key);
CREATE INDEX IF NOT EXISTS idx_fact_to_account ON fact_transactions(to_account_key);
CREATE INDEX IF NOT EXISTS idx_fact_from_bank ON fact_transactions(from_bank_key);
CREATE INDEX IF NOT EXISTS idx_fact_composite_fraud_amount ON fact_transactions(is_laundering, amount_paid);

-- ============================================================================
-- SECTION 2: EXPLAIN PLAN BENCHMARKS & JOIN STRATEGIES
-- ============================================================================

-- Benchmark 1: Unindexed Full Table Scan vs Indexed Filter
EXPLAIN SELECT * FROM fact_transactions WHERE is_laundering = 1 AND amount_paid > 50000;

-- Benchmark 2: Foreign Key Join Strategy
EXPLAIN SELECT f.transaction_id, f.amount_paid, b.bank_name
FROM fact_transactions f
JOIN dim_bank b ON f.from_bank_key = b.bank_key
WHERE f.is_laundering = 1;

-- Benchmark 3: Composite Date Range + Fraud Flag Filter Scan
EXPLAIN SELECT f.transaction_id, f.amount_paid, t.full_timestamp
FROM fact_transactions f
JOIN dim_time t ON f.time_key = t.time_key
WHERE f.time_key >= 202601010000 AND f.is_laundering = 1;

SELECT 'Query optimization benchmark and indexing DDL initialized successfully' AS status;
