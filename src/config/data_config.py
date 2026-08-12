"""
Centralized Configuration Module for Data Validation, Cleaning, & Fraud System Constants.
"""
from pathlib import Path

# System Paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "transactions.parquet"
CLEAN_DATA_PATH = PROJECT_ROOT / "data" / "cleaned" / "transactions_clean.parquet"
REPORT_PATH = PROJECT_ROOT / "docs" / "Data_Quality_Report.md"

# Polars Display & System Settings
SEED = 42
POLARS_DISPLAY_ROWS = 20
POLARS_DISPLAY_COLUMNS = 20

# Column Renaming Mapping
COLUMN_RENAMING_MAP = {
    "Account": "From_Account",
    "Account_duplicated_0": "To_Account",
    "From Bank": "From_Bank",
    "To Bank": "To_Bank",
    "Amount Paid": "Amount_Paid",
    "Amount Received": "Amount_Received",
    "Payment Currency": "Payment_Currency",
    "Receiving Currency": "Receiving_Currency",
    "Payment Format": "Payment_Format",
    "Is Laundering": "Is_Laundering"
}

# Domain Rule Constants & Allowed Categories
ALLOWED_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY", "INR", "BRL"]
ALLOWED_PAYMENT_FORMATS = [
    "Credit Card", "Debit Card", "ACH", "Wire", "Cheque",
    "Cash", "Rebalancing", "Cross Border", "Bitcoin"
]

# Business Thresholds & Risk Limits
MAX_TRANSACTION_AMOUNT = 100000000.0  # $100M upper limit
MIN_TRANSACTION_AMOUNT = 0.01          # $0.01 lower limit
OUTLIER_IQR_FACTOR = 3.0              # Extreme outlier multiplier threshold
EXPECTED_DATETIME_FORMAT = "%Y/%m/%d %H:%M"

# Quality Thresholds
LOW_MISSING_THRESHOLD = 5.0            # < 5%
HIGH_MISSING_THRESHOLD = 20.0          # > 20%
QUALITY_THRESHOLD_EXCELLENT = 99.0
QUALITY_THRESHOLD_GOOD = 95.0

# Database Key Schema Definitions
PRIMARY_KEY = "TransactionID"
FOREIGN_KEYS = ["From_Account", "To_Account", "From_Bank", "To_Bank"]

# Expected Data Schema
EXPECTED_SCHEMA = {
    "TransactionID": "String",
    "Timestamp": "Datetime",
    "From_Bank": "Int64",
    "From_Account": "String",
    "To_Bank": "Int64",
    "To_Account": "String",
    "Amount_Paid": "Float64",
    "Payment_Currency": "String",
    "Amount_Received": "Float64",
    "Receiving_Currency": "String",
    "Payment_Format": "String",
    "Is_Laundering": "Int64"
}
