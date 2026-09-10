"""
Configuration and Path Management for Flight Delay Analysis Project.
Defines canonical directories, SQLite database connection helpers, and FAA cost constants.
"""

from pathlib import Path
import sqlite3

# Canonical Directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
SQL_DIR = PROJECT_ROOT / "sql"
REPORTS_DIR = PROJECT_ROOT / "reports"
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"
TESTS_DIR = PROJECT_ROOT / "tests"

# Database Configuration
DB_PATH = DATA_DIR / "flight_delays.db"

# FAA & Airlines for America (A4A) Economic Benchmarks
# References: FAA APO-130 Economic Values for FAA Investment and Regulatory Decisions;
# Airlines for America (A4A) U.S. Passenger Airline Cost of Delay: $74.24/min direct aircraft operating cost.
AIRCRAFT_COST_PER_DELAY_MINUTE = 74.24  # USD per minute of arrival delay
PASSENGER_VALUE_OF_TIME_PER_MINUTE = 35.00  # USD per passenger delay minute

# Ensure critical runtime directories exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def get_db_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """
    Establishes an optimized SQLite connection with foreign keys and WAL mode.
    Returns:
        sqlite3.Connection: Configured SQLite connection.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn
