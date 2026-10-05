"""Local SQLite investigation register with append-only change history."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone

STATUSES=['New','In review','Resolved','Dismissed']

@contextmanager
def connect(path):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(path)
    conn.row_factory=sqlite3.Row
    conn.execute('CREATE TABLE IF NOT EXISTS cases (transaction_id TEXT PRIMARY KEY, status TEXT, reviewer TEXT, notes TEXT, version INTEGER, updated_at TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS case_history (id INTEGER PRIMARY KEY, transaction_id TEXT, status TEXT, reviewer TEXT, notes TEXT, version INTEGER, updated_at TEXT)')
    try:
        with conn:
            yield conn
    finally:
        conn.close()

def get_case(path,transaction_id):
    with connect(path) as conn:
        row=conn.execute('SELECT * FROM cases WHERE transaction_id=?',(str(transaction_id),)).fetchone()
    return dict(row) if row else None

def save_case(path,transaction_id,status,reviewer,notes,expected_version=0):
    if status not in STATUSES or not str(transaction_id).strip():
        raise ValueError('Valid transaction ID and status required.')
    with connect(path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        current=conn.execute('SELECT version FROM cases WHERE transaction_id=?',(str(transaction_id),)).fetchone()
        version=current['version'] if current else 0
        if version!=expected_version:
            raise ValueError('Case changed; reload before saving.')
        values=(str(transaction_id),status,reviewer,notes,version+1,datetime.now(timezone.utc).isoformat())
        conn.execute('INSERT OR REPLACE INTO cases VALUES (?,?,?,?,?,?)',values)
        conn.execute('INSERT INTO case_history (transaction_id,status,reviewer,notes,version,updated_at) VALUES (?,?,?,?,?,?)',values)
    return get_case(path,transaction_id)

def history(path,transaction_id):
    with connect(path) as conn:
        return [dict(row) for row in conn.execute('SELECT * FROM case_history WHERE transaction_id=? ORDER BY version',(str(transaction_id),))]
