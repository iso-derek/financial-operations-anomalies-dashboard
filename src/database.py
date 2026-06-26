"""SQLite storage utilities for the finance operations project."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLEAN_PATH = PROJECT_ROOT / "data" / "processed" / "clean_finance_operations.csv"
DB_PATH = PROJECT_ROOT / "data" / "processed" / "finance_operations.db"
TABLE_NAME = "transactions"


def create_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def load_clean_data(clean_path: Path = CLEAN_PATH) -> pd.DataFrame:
    if not clean_path.exists():
        raise FileNotFoundError(
            f"Clean data not found at {clean_path}. Run `python src/clean_data.py` first."
        )
    return pd.read_csv(clean_path)


def write_transactions_to_sqlite(
    clean_path: Path = CLEAN_PATH,
    db_path: Path = DB_PATH,
    table_name: str = TABLE_NAME,
) -> None:
    df = load_clean_data(clean_path)
    with create_connection(db_path) as conn:
        df.to_sql(table_name, conn, if_exists="replace", index=False)


def read_transactions(
    db_path: Path = DB_PATH,
    table_name: str = TABLE_NAME,
    limit: int | None = None,
) -> pd.DataFrame:
    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found at {db_path}. Run `python src/database.py` first."
        )
    query = f"SELECT * FROM {table_name}"
    if limit:
        query += f" LIMIT {int(limit)}"
    with create_connection(db_path) as conn:
        return pd.read_sql_query(query, conn)


def run_query(query: str, db_path: Path = DB_PATH) -> pd.DataFrame:
    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found at {db_path}. Run `python src/database.py` first."
        )
    with create_connection(db_path) as conn:
        return pd.read_sql_query(query, conn)


def main() -> None:
    write_transactions_to_sqlite()
    row_count = len(read_transactions(limit=None))
    print(f"Wrote {row_count:,} rows to {DB_PATH} table `{TABLE_NAME}`")


if __name__ == "__main__":
    main()
