-- 07_online_feature_store_schema.sql: Online Feature Store Schema, Indexes & Version Control

CREATE TABLE IF NOT EXISTS schema_version (
    version INT PRIMARY KEY,
    description VARCHAR(255) NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO schema_version (version, description)
VALUES (1, 'Online Feature Store Hardening Schema v1')
ON CONFLICT (version) DO NOTHING;

CREATE TABLE IF NOT EXISTS account_states (
    account_id VARCHAR(100) PRIMARY KEY,
    transaction_count BIGINT NOT NULL DEFAULT 0,
    total_amount_paid DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    total_amount_received DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    amount_sum_sq DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    last_transaction_timestamp TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transaction_history (
    transaction_key VARCHAR(100) PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    from_account VARCHAR(100) NOT NULL,
    to_account VARCHAR(100) NOT NULL,
    from_bank VARCHAR(100) NOT NULL,
    to_bank VARCHAR(100) NOT NULL,
    amount_paid DOUBLE PRECISION NOT NULL,
    amount_received DOUBLE PRECISION NOT NULL,
    payment_format VARCHAR(50) NOT NULL,
    payment_currency VARCHAR(10) NOT NULL,
    receiving_currency VARCHAR(10) NOT NULL,
    is_laundering INT DEFAULT 0 NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tx_from_acct_ts ON transaction_history (from_account, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_tx_to_acct_ts ON transaction_history (to_account, timestamp DESC);
