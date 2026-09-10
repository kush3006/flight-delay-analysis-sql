"""
Automated Test Suite for Flight Delay Analysis SQL Project.
Validates database schema, relational constraints, domain logic,
delay mathematical equality, and query execution performance.
"""

from pathlib import Path
import sqlite3
import sys
import time
import pytest
import pandas as pd

# Add parent directory to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from src.config import DB_PATH, SQL_DIR, get_db_connection
from src.run_analysis import split_sql_queries


@pytest.fixture(scope="module")
def db_conn():
    """Provides a thread-safe connection to the flight delay SQLite database."""
    assert DB_PATH.exists(), f"Database file does not exist at {DB_PATH}. Run seed_database.py first."
    conn = get_db_connection(DB_PATH)
    yield conn
    conn.close()


def test_database_table_counts(db_conn):
    """Verifies that primary dimensions and fact tables are non-empty and properly scaled."""
    cursor = db_conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM airlines;")
    airline_count = cursor.fetchone()[0]
    assert airline_count == 12, f"Expected 12 airlines, got {airline_count}"

    cursor.execute("SELECT COUNT(*) FROM airports;")
    airport_count = cursor.fetchone()[0]
    assert airport_count == 30, f"Expected 30 airports, got {airport_count}"

    cursor.execute("SELECT COUNT(*) FROM flights;")
    flight_count = cursor.fetchone()[0]
    assert flight_count >= 50000, f"Expected >= 50,000 flight records, got {flight_count}"


def test_foreign_key_integrity(db_conn):
    """Asserts that zero foreign key violations exist in the database."""
    cursor = db_conn.cursor()
    cursor.execute("PRAGMA foreign_key_check;")
    violations = cursor.fetchall()
    assert len(violations) == 0, f"Foreign key integrity check failed with violations: {violations}"


def test_data_hygiene_and_constraints(db_conn):
    """Asserts that operational values adhere to physical constraints."""
    cursor = db_conn.cursor()

    # No negative distances
    cursor.execute("SELECT COUNT(*) FROM flights WHERE distance <= 0;")
    assert cursor.fetchone()[0] == 0, "Found flights with negative or zero distance."

    # Origin airport cannot equal destination airport
    cursor.execute("SELECT COUNT(*) FROM flights WHERE origin_airport = dest_airport;")
    assert cursor.fetchone()[0] == 0, "Found flights where origin airport equals destination airport."

    # Cancelled flights must have valid cancellation code
    cursor.execute("SELECT COUNT(*) FROM flights WHERE cancelled = 1 AND cancellation_code NOT IN ('A', 'B', 'C', 'D');")
    assert cursor.fetchone()[0] == 0, "Found cancelled flights with invalid or missing cancellation codes."

    # Completed flights must have non-null actual departure time
    cursor.execute("SELECT COUNT(*) FROM flights WHERE cancelled = 0 AND dep_time IS NULL;")
    assert cursor.fetchone()[0] == 0, "Found completed flights missing actual departure time."


def test_bts_delay_sum_mathematical_consistency(db_conn):
    """
    Asserts the Bureau of Transportation Statistics rule:
    For all flights with arrival delay >= 15 minutes, the sum of delay attributions
    (carrier + weather + nas + security + late_aircraft) must equal arr_delay.
    """
    cursor = db_conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) 
        FROM flights 
        WHERE arr_delay >= 15 
          AND cancelled = 0 
          AND diverted = 0 
          AND (carrier_delay + weather_delay + nas_delay + security_delay + late_aircraft_delay) <> arr_delay;
    """)
    discrepancy_count = cursor.fetchone()[0]
    assert discrepancy_count == 0, f"Found {discrepancy_count} delayed records where delay breakdown does not sum to arrival delay."


def test_master_view_integrity(db_conn):
    """Verifies that the operational master reporting view compiles and outputs data."""
    df_sample = pd.read_sql_query("SELECT * FROM v_flights_operational_master LIMIT 50;", db_conn)
    assert len(df_sample) == 50
    assert "is_on_time_otp15" in df_sample.columns
    assert "en_route_delay_delta" in df_sample.columns
    assert "estimated_cost_usd" in df_sample.columns


@pytest.mark.parametrize("sql_file", [
    "02_data_cleaning_and_audit.sql",
    "03_operational_kpis.sql",
    "04_carrier_benchmarking.sql",
    "05_hub_and_route_bottlenecks.sql",
    "06_delay_root_cause_analysis.sql",
    "07_advanced_window_functions.sql",
    "08_financial_impact_and_roi.sql",
])
def test_sql_scripts_execution_and_performance(db_conn, sql_file):
    """
    Executes each analytical query in each SQL file, asserting:
    1. Zero SQL execution exceptions.
    2. Execution completes in sub-second time (performance indexing verification).
    """
    file_path = SQL_DIR / sql_file
    assert file_path.exists(), f"SQL script missing: {sql_file}"

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    queries = split_sql_queries(content)
    assert len(queries) > 0, f"No queries parsed from {sql_file}"

    for title, sql_code in queries:
        t_start = time.perf_counter()
        df = pd.read_sql_query(sql_code, db_conn)
        elapsed_sec = time.perf_counter() - t_start

        assert df is not None
        # Performance benchmark: Each query must execute within 2.5 seconds on 100k records
        assert elapsed_sec < 2.5, f"Query '{title}' in {sql_file} exceeded performance SLA ({elapsed_sec:.2f}s > 2.5s)"
