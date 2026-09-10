"""
Database Seeder and High-Speed Bulk Ingestion Engine.
Executes relational DDL, populates dimensions and fact tables using atomic transactions,
and validates row counts and foreign key constraints.
"""

import argparse
from pathlib import Path
import sqlite3
import sys
import time
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import DB_PATH, RAW_DATA_DIR, SQL_DIR, get_db_connection
from src.generate_data import save_datasets


def execute_sql_file(conn: sqlite3.Connection, sql_path: Path) -> None:
    """Reads and executes a multi-statement SQL script."""
    print(f"[-] Executing SQL script: {sql_path.name}...")
    with open(sql_path, "r", encoding="utf-8") as f:
        script = f.read()
    cursor = conn.cursor()
    cursor.executescript(script)
    conn.commit()


def seed_database(num_records: int = 100000, force_regenerate: bool = False) -> None:
    """
    Populates SQLite database from raw CSVs or generates them on demand.
    
    Args:
        num_records (int): Target flight records.
        force_regenerate (bool): Whether to force recreate raw CSV files.
    """
    start_time = time.time()
    print("=================================================================")
    print("      FLIGHT DELAY ANALYTICS - DATABASE SEEDING ENGINE           ")
    print("=================================================================")

    airlines_csv = RAW_DATA_DIR / "airlines.csv"
    airports_csv = RAW_DATA_DIR / "airports.csv"
    flights_csv = RAW_DATA_DIR / "flights.csv"

    # Step 1: Ensure Raw CSV files exist
    if force_regenerate or not (airlines_csv.exists() and airports_csv.exists() and flights_csv.exists()):
        print("[!] Generating synthetic flight operational dataset...")
        save_datasets(num_records=num_records)
    else:
        print("[OK] Found existing raw CSV files in data/raw/")

    # Step 2: Establish DB connection and run Schema DDL
    if DB_PATH.exists():
        print(f"[!] Removing existing database file: {DB_PATH.name}")
        DB_PATH.unlink()

    conn = get_db_connection(DB_PATH)
    schema_sql = SQL_DIR / "01_schema_and_indexes.sql"
    execute_sql_file(conn, schema_sql)

    # Step 3: Fast Batch Insertion using Pandas + SQLite chunked inserts
    cursor = conn.cursor()

    # Load Airlines
    print("[-] Ingesting master airlines dimension...")
    df_airlines = pd.read_csv(airlines_csv)
    df_airlines.to_sql("airlines", conn, if_exists="append", index=False)
    print(f"[OK] Ingested {len(df_airlines)} airlines.")

    # Load Airports
    print("[-] Ingesting master airports dimension...")
    df_airports = pd.read_csv(airports_csv)
    df_airports.to_sql("airports", conn, if_exists="append", index=False)
    print(f"[OK] Ingested {len(df_airports)} airports.")

    # Load Flights in chunks with progress reporting
    print(f"[-] Ingesting flights fact table from {flights_csv.name}...")
    chunk_size = 25000
    total_loaded = 0
    
    for chunk in pd.read_csv(flights_csv, chunksize=chunk_size):
        chunk.to_sql("flights", conn, if_exists="append", index=False)
        total_loaded += len(chunk)
        print(f"    -> Ingested {total_loaded:,} flight records...")

    # Step 4: Verification & Sanity Check
    print("[-] Verifying database integrity...")
    cursor.execute("PRAGMA foreign_key_check;")
    fk_errors = cursor.fetchall()
    if fk_errors:
        print(f"[ERROR] Foreign key constraint violations found: {fk_errors}")
    else:
        print("[OK] Foreign key integrity: PASSED (0 violations).")

    cursor.execute("SELECT COUNT(*) FROM flights;")
    flight_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM v_flights_operational_master;")
    view_count = cursor.fetchone()[0]

    elapsed = time.time() - start_time
    print("-----------------------------------------------------------------")
    print(f"[OK] DATABASE SEEDING COMPLETED SUCCESSFULLY IN {elapsed:.2f}s")
    print(f"    - Database Path: {DB_PATH.resolve()}")
    print(f"    - Total Flights: {flight_count:,}")
    print(f"    - Master View Rows: {view_count:,}")
    print("=================================================================")

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed flight delay SQLite database.")
    parser.add_argument("--records", type=int, default=100000, help="Flight records to generate")
    parser.add_argument("--force", action="store_true", help="Force regenerate CSVs")
    args = parser.parse_args()

    seed_database(num_records=args.records, force_regenerate=args.force)
