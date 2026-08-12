"""
Script for Stage 4: DuckDB Data Warehouse Ingestion for LI-Large dataset.
Populates fact_transactions, dim_accounts, and dim_banks star-schema tables.
"""
import os
import sys
import time

import duckdb

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("=" * 60)
    print("STAGE 4: DUCKDB DATA WAREHOUSE BUILD (LI-LARGE)")
    print("=" * 60)

    start_time = time.time()
    parquet_path = "data/cleaned/transactions_clean.parquet"
    accounts_csv_path = "data/raw/LI-Large_accounts.csv"
    db_path = "data/warehouse.duckdb"

    if os.path.exists(db_path):
        os.remove(db_path)

    conn = duckdb.connect(db_path)

    print(f"Creating star schema tables from {parquet_path}...")

    # Fact Transactions
    conn.execute(f"""
        CREATE TABLE fact_transactions AS 
        SELECT 
            TransactionID,
            Timestamp,
            From_Bank,
            From_Account,
            To_Bank,
            To_Account,
            Amount_Received,
            Receiving_Currency,
            Amount_Paid,
            Payment_Currency,
            Payment_Format,
            Is_Laundering
        FROM read_parquet('{parquet_path}');
    """)

    # Create indexes for optimal querying
    print("Creating indexes on fact_transactions...")
    conn.execute("CREATE INDEX idx_tx_timestamp ON fact_transactions(Timestamp);")
    conn.execute("CREATE INDEX idx_tx_from_account ON fact_transactions(From_Account);")

    # Dim Banks
    print("Creating dim_banks...")
    conn.execute("""
        CREATE TABLE dim_banks AS
        SELECT DISTINCT From_Bank AS Bank_ID FROM fact_transactions
        UNION
        SELECT DISTINCT To_Bank AS Bank_ID FROM fact_transactions;
    """)

    # Dim Accounts
    print("Creating dim_accounts...")
    if os.path.exists(accounts_csv_path):
        conn.execute(f"""
            CREATE TABLE dim_accounts AS
            SELECT 
                "Bank Name" AS Bank_Name,
                "Bank ID" AS Bank_ID,
                "Account Number" AS Account_Number,
                "Entity ID" AS Entity_ID,
                "Entity Name" AS Entity_Name
            FROM read_csv_auto('{accounts_csv_path}');
        """)
    else:
        conn.execute("""
            CREATE TABLE dim_accounts AS
            SELECT DISTINCT From_Account AS Account_Number, From_Bank AS Bank_ID FROM fact_transactions
            UNION
            SELECT DISTINCT To_Account AS Account_Number, To_Bank AS Bank_ID FROM fact_transactions;
        """)

    # Verification
    tx_count = conn.execute("SELECT COUNT(*) FROM fact_transactions;").fetchone()[0]
    bank_count = conn.execute("SELECT COUNT(*) FROM dim_banks;").fetchone()[0]
    acc_count = conn.execute("SELECT COUNT(*) FROM dim_accounts;").fetchone()[0]

    print("\nWarehouse Verification:")
    print(f"fact_transactions: {tx_count:,} rows")
    print(f"dim_banks: {bank_count:,} rows")
    print(f"dim_accounts: {acc_count:,} rows")

    conn.close()

    print("\n✅ STAGE 4 COMPLETE: DuckDB warehouse built successfully.")
    print(f"Elapsed Time: {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    main()
