-- 01_schema.sql: Enterprise Data Warehouse DDL, Explicit Constraints, Foreign Keys, Audit Metadata, & Indexes
-- Author: Hardik Gautam | Phase 2 & 3 Data Warehouse Infrastructure

-- 1. Infrastructure Schemas
CREATE SCHEMA IF NOT EXISTS warehouse_schema;
CREATE SCHEMA IF NOT EXISTS staging_schema;
CREATE SCHEMA IF NOT EXISTS audit_schema;

-- 2. Star Schema Dimension DDL
CREATE TABLE IF NOT EXISTS dim_time (
    time_key INT CONSTRAINT pk_dim_time PRIMARY KEY,
    full_timestamp TIMESTAMP NOT NULL,
    year INT NOT NULL CONSTRAINT chk_time_year CHECK (year >= 2000),
    quarter INT NOT NULL CONSTRAINT chk_time_quarter CHECK (quarter BETWEEN 1 AND 4),
    month INT NOT NULL CONSTRAINT chk_time_month CHECK (month BETWEEN 1 AND 12),
    month_name VARCHAR(15) NOT NULL,
    day INT NOT NULL CONSTRAINT chk_time_day CHECK (day BETWEEN 1 AND 31),
    day_of_week INT NOT NULL CONSTRAINT chk_time_weekday CHECK (day_of_week BETWEEN 1 AND 7),
    day_name VARCHAR(15) NOT NULL,
    hour INT NOT NULL CONSTRAINT chk_time_hour CHECK (hour BETWEEN 0 AND 23),
    minute INT NOT NULL CONSTRAINT chk_time_minute CHECK (minute BETWEEN 0 AND 59),
    is_weekend BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_bank (
    bank_key INTEGER CONSTRAINT pk_dim_bank PRIMARY KEY,
    bank_id INT NOT NULL CONSTRAINT uk_dim_bank_id UNIQUE,
    bank_name VARCHAR(100) NOT NULL,
    country_code VARCHAR(10) DEFAULT 'US' NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_current BOOLEAN DEFAULT TRUE NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_account (
    account_key INTEGER CONSTRAINT pk_dim_account PRIMARY KEY,
    account_number VARCHAR(50) NOT NULL CONSTRAINT uk_dim_account_num UNIQUE,
    bank_id INT NOT NULL,
    account_type VARCHAR(20) DEFAULT 'Checking' NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_current BOOLEAN DEFAULT TRUE NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_currency (
    currency_key INTEGER CONSTRAINT pk_dim_currency PRIMARY KEY,
    currency_code VARCHAR(10) NOT NULL CONSTRAINT uk_dim_currency_code UNIQUE,
    currency_name VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_payment_format (
    payment_format_key INTEGER CONSTRAINT pk_dim_payment_format PRIMARY KEY,
    format_name VARCHAR(50) NOT NULL CONSTRAINT uk_dim_payment_format UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 3. Star Schema Fact DDL with Explicit Foreign Keys & Check Constraints
CREATE TABLE IF NOT EXISTS fact_transactions (
    transaction_key INTEGER CONSTRAINT pk_fact_transactions PRIMARY KEY,
    transaction_id VARCHAR(100) NOT NULL CONSTRAINT uk_fact_transaction_id UNIQUE,
    time_key INT NOT NULL CONSTRAINT fk_fact_time REFERENCES dim_time(time_key),
    from_bank_key INT NOT NULL CONSTRAINT fk_fact_from_bank REFERENCES dim_bank(bank_key),
    from_account_key INT NOT NULL CONSTRAINT fk_fact_from_account REFERENCES dim_account(account_key),
    to_bank_key INT NOT NULL CONSTRAINT fk_fact_to_bank REFERENCES dim_bank(bank_key),
    to_account_key INT NOT NULL CONSTRAINT fk_fact_to_account REFERENCES dim_account(account_key),
    payment_format_key INT NOT NULL CONSTRAINT fk_fact_payment_format REFERENCES dim_payment_format(payment_format_key),
    payment_currency_key INT NOT NULL CONSTRAINT fk_fact_payment_currency REFERENCES dim_currency(currency_key),
    receiving_currency_key INT NOT NULL CONSTRAINT fk_fact_receiving_currency REFERENCES dim_currency(currency_key),
    amount_paid NUMERIC(18,2) NOT NULL CONSTRAINT chk_fact_amount_paid CHECK (amount_paid >= 0),
    amount_received NUMERIC(18,2) NOT NULL CONSTRAINT chk_fact_amount_received CHECK (amount_received >= 0),
    is_amount_outlier INT DEFAULT 0 NOT NULL CONSTRAINT chk_fact_outlier CHECK (is_amount_outlier IN (0,1)),
    is_laundering INT DEFAULT 0 NOT NULL CONSTRAINT chk_fact_laundering CHECK (is_laundering IN (0,1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 4. Enterprise Audit & Metadata Tables
CREATE TABLE IF NOT EXISTS etl_pipeline_log (
    log_id INTEGER PRIMARY KEY,
    run_id VARCHAR(50) NOT NULL,
    pipeline_name VARCHAR(100) NOT NULL,
    pipeline_version VARCHAR(20) DEFAULT '2.0.0' NOT NULL,
    git_commit VARCHAR(50) DEFAULT 'HEAD' NOT NULL,
    status VARCHAR(20) NOT NULL,
    rows_extracted INT NOT NULL,
    rows_inserted INT NOT NULL,
    rows_skipped INT DEFAULT 0 NOT NULL,
    execution_duration_sec NUMERIC(10,3) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS etl_dataset_metadata (
    metadata_id INTEGER PRIMARY KEY,
    dataset_name VARCHAR(100) NOT NULL,
    record_count INT NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    source_file VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS etl_error_log (
    error_id INTEGER PRIMARY KEY,
    run_id VARCHAR(50) NOT NULL,
    stage_name VARCHAR(100) NOT NULL,
    error_message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 5. Enterprise B-Tree Performance Indexes
CREATE INDEX IF NOT EXISTS idx_fact_time_key ON fact_transactions(time_key);
CREATE INDEX IF NOT EXISTS idx_fact_from_bank ON fact_transactions(from_bank_key);
CREATE INDEX IF NOT EXISTS idx_fact_from_account ON fact_transactions(from_account_key);
CREATE INDEX IF NOT EXISTS idx_fact_to_bank ON fact_transactions(to_bank_key);
CREATE INDEX IF NOT EXISTS idx_fact_to_account ON fact_transactions(to_account_key);
CREATE INDEX IF NOT EXISTS idx_fact_is_laundering ON fact_transactions(is_laundering);
CREATE INDEX IF NOT EXISTS idx_fact_composite_fraud_amount ON fact_transactions(is_laundering, amount_paid);
