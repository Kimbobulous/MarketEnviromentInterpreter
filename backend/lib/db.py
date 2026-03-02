"""SQLite helpers for MEI snapshot persistence."""

from __future__ import annotations

import os
import sqlite3

from .market_data.cache import ensure_market_cache_table


DEFAULT_DB_FILENAME = "mei.db"


def get_db_path() -> str:
    """Return configured SQLite DB path and ensure parent directory exists."""
    configured = os.getenv("MEI_DB_PATH")
    if configured:
        db_path = configured
    else:
        backend_dir = os.path.dirname(os.path.dirname(__file__))
        db_path = os.path.join(backend_dir, "data", DEFAULT_DB_FILENAME)

    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    return db_path


def connect(db_path: str | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with row access by column name."""
    target = db_path or get_db_path()
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create persistence tables when absent."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tab TEXT NOT NULL,
            created_at TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            status TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            tab TEXT NOT NULL,
            action TEXT NOT NULL,
            detail TEXT
        )
        """
    )

    ensure_market_cache_table(conn)

    conn.commit()
