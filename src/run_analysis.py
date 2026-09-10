"""
CLI Query Execution & Benchmarking Runner.
Parses, benchmarks, and displays results of SQL analytics queries.
Outputs formatted ASCII tables with execution timings in milliseconds.
"""

import argparse
from pathlib import Path
import re
import sqlite3
import sys
import time
import pandas as pd

# Add parent directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import DB_PATH, SQL_DIR, get_db_connection


def split_sql_queries(sql_content: str) -> list[tuple[str, str]]:
    """
    Extracts individual analytical queries and their descriptive header comments.
    
    Returns:
        list[tuple[str, str]]: (query_title, query_sql)
    """
    # Regex pattern to match Query X headers
    pattern = re.compile(r"(--\s*Query\s*\d+:.*?\n)(.*?)(?=--\s*Query\s*\d+:|$)", re.DOTALL | re.IGNORECASE)
    matches = pattern.findall(sql_content)

    queries = []
    if matches:
        for header, body in matches:
            title = header.strip().lstrip("-").strip()
            # Clean comments from the body
            clean_body = body.strip().rstrip(";")
            if clean_body:
                queries.append((title, clean_body))
    else:
        # Fallback: split by semicolon
        raw_queries = sql_content.split(";")
        for i, q in enumerate(raw_queries):
            clean_q = q.strip()
            if clean_q and not clean_q.startswith("--") and len(clean_q) > 10:
                queries.append((f"Query {i+1}", clean_q))

    return queries


def run_sql_file(conn: sqlite3.Connection, file_path: Path, max_rows: int = 15) -> None:
    """Executes all queries inside a SQL file and prints formatted tables with benchmarking."""
    print("\n" + "=" * 80)
    print(f" EXECUTING SCRIPT: {file_path.name}")
    print("=" * 80)

    if not file_path.exists():
        print(f"[ERROR] File not found: {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    queries = split_sql_queries(content)
    if not queries:
        print("[!] No distinct queries parsed from file.")
        return

    for idx, (title, sql_code) in enumerate(queries, 1):
        print("\n" + "-" * 80)
        print(f"[{idx}/{len(queries)}] {title}")
        print("-" * 80)

        t_start = time.perf_counter()
        try:
            df = pd.read_sql_query(sql_code, conn)
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0

            if df.empty:
                print("(Query returned 0 rows)")
            else:
                print(df.head(max_rows).to_string(index=False))
                if len(df) > max_rows:
                    print(f"... ({len(df) - max_rows} more rows truncated for display)")

            print(f"\n[Execution Time: {elapsed_ms:.2f} ms | Rows Returned: {len(df)}]")
        except Exception as e:
            print(f"[ERROR] Failed to execute query:\n{e}")


def main():
    parser = argparse.ArgumentParser(description="Run and benchmark SQL analytics suite.")
    parser.add_argument("--file", type=str, default=None, help="Specific SQL filename (e.g. 03_operational_kpis.sql)")
    parser.add_argument("--all", action="store_true", help="Execute all SQL scripts in sequential order")
    parser.add_argument("--limit", type=int, default=15, help="Max rows to display per table (default: 15)")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"[ERROR] Database file not found at {DB_PATH}. Please run seed_database.py first.")
        sys.exit(1)

    conn = get_db_connection(DB_PATH)

    sql_files = sorted([f for f in SQL_DIR.glob("*.sql") if not f.name.startswith("01_")])

    if args.all:
        for sql_file in sql_files:
            run_sql_file(conn, sql_file, max_rows=args.limit)
    elif args.file:
        target_path = SQL_DIR / args.file
        if not target_path.exists():
            # Try finding with partial name
            matching = [f for f in sql_files if args.file in f.name]
            if matching:
                target_path = matching[0]
            else:
                print(f"[ERROR] SQL file not found matching '{args.file}'")
                sys.exit(1)
        run_sql_file(conn, target_path, max_rows=args.limit)
    else:
        # Default: run 03_operational_kpis.sql
        default_file = SQL_DIR / "03_operational_kpis.sql"
        run_sql_file(conn, default_file, max_rows=args.limit)

    conn.close()


if __name__ == "__main__":
    main()
