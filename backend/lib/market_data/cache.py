"""SQLite cache helpers for market data fetches."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import sqlite3


def ensure_market_cache_table(conn: sqlite3.Connection) -> None:
    """Create market_cache table when absent."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS market_cache (
            cache_key TEXT PRIMARY KEY,
            fetched_at TEXT NOT NULL,
            data_json TEXT NOT NULL
        )
        """
    )
    conn.commit()


def cache_get(
    conn: sqlite3.Connection,
    key: str,
    max_age_seconds: int,
) -> list[dict] | None:
    """Return cached rows when entry exists and has not expired."""
    row = conn.execute(
        """
        SELECT fetched_at, data_json
        FROM market_cache
        WHERE cache_key = ?
        LIMIT 1
        """,
        (key,),
    ).fetchone()

    if row is None:
        return None

    fetched_at = _parse_iso(row["fetched_at"])
    if fetched_at is None:
        return None

    age_seconds = (datetime.now(timezone.utc) - fetched_at).total_seconds()
    if age_seconds > max_age_seconds:
        return None

    try:
        payload = json.loads(row["data_json"])
    except (TypeError, json.JSONDecodeError):
        return None

    if not isinstance(payload, list):
        return None

    return payload


def cache_put(conn: sqlite3.Connection, key: str, rows: list[dict]) -> None:
    """Write cached rows with current UTC timestamp."""
    fetched_at = datetime.now(timezone.utc).isoformat()
    data_json = json.dumps(rows, separators=(",", ":"), sort_keys=True)

    conn.execute(
        """
        INSERT INTO market_cache (cache_key, fetched_at, data_json)
        VALUES (?, ?, ?)
        ON CONFLICT(cache_key) DO UPDATE SET
            fetched_at = excluded.fetched_at,
            data_json = excluded.data_json
        """,
        (key, fetched_at, data_json),
    )
    conn.commit()


def get_cache_entry(conn: sqlite3.Connection, key: str) -> dict | None:
    """Return metadata for a cache key including row count."""
    row = conn.execute(
        """
        SELECT fetched_at, data_json
        FROM market_cache
        WHERE cache_key = ?
        LIMIT 1
        """,
        (key,),
    ).fetchone()

    if row is None:
        return None

    fetched_at = row["fetched_at"]
    parsed = _parse_iso(fetched_at)

    rows_count = 0
    try:
        payload = json.loads(row["data_json"])
        if isinstance(payload, list):
            rows_count = len(payload)
    except (TypeError, json.JSONDecodeError):
        rows_count = 0

    return {
        "fetched_at": fetched_at if isinstance(fetched_at, str) else "",
        "fetched_dt": parsed,
        "rows": rows_count,
    }


def get_fetched_at(conn: sqlite3.Connection, key: str) -> str | None:
    """Return fetched_at for cache key when present."""
    row = conn.execute(
        """
        SELECT fetched_at
        FROM market_cache
        WHERE cache_key = ?
        LIMIT 1
        """,
        (key,),
    ).fetchone()
    if row is None:
        return None
    value = row["fetched_at"]
    return value if isinstance(value, str) and value else None


def _parse_iso(value: str | None) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
