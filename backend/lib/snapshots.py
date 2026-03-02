"""Snapshot persistence and retrieval helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
import sqlite3


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def derive_payload_status(payload: dict) -> str:
    """Aggregate panel statuses into payload-level status."""
    panels = payload.get("panels", []) if isinstance(payload, dict) else []
    statuses = []

    if isinstance(panels, list):
        for panel in panels:
            if isinstance(panel, dict):
                raw = panel.get("status")
                if isinstance(raw, str):
                    statuses.append(raw.lower())

    if any(status == "error" for status in statuses):
        return "error"
    if any(status == "partial" for status in statuses):
        return "partial"
    return "ok"


def log_action(
    conn: sqlite3.Connection, tab: str, action: str, detail: str | None = None
) -> None:
    """Write an audit-log event."""
    conn.execute(
        """
        INSERT INTO audit_log (created_at, tab, action, detail)
        VALUES (?, ?, ?, ?)
        """,
        (_iso_now(), tab, action, detail),
    )
    conn.commit()


def save_snapshot(conn: sqlite3.Connection, tab: str, payload: dict) -> int:
    """Persist payload JSON into snapshots and emit an audit event."""
    created_at = payload.get("last_updated") if isinstance(payload, dict) else None
    if not isinstance(created_at, str) or not created_at.strip():
        created_at = _iso_now()

    status = derive_payload_status(payload)
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)

    cursor = conn.execute(
        """
        INSERT INTO snapshots (tab, created_at, payload_json, status)
        VALUES (?, ?, ?, ?)
        """,
        (tab, created_at, payload_json, status),
    )
    conn.commit()

    snapshot_id = int(cursor.lastrowid)
    log_action(
        conn,
        tab,
        "snapshot_saved",
        f"snapshot_id={snapshot_id}; status={status}",
    )
    return snapshot_id


def get_last_good_snapshot(conn: sqlite3.Connection, tab: str) -> dict | None:
    """Return newest non-error payload for a tab, or None when unavailable."""
    row = conn.execute(
        """
        SELECT payload_json
        FROM snapshots
        WHERE tab = ?
          AND status IN ('ok', 'partial')
        ORDER BY id DESC
        LIMIT 1
        """,
        (tab,),
    ).fetchone()

    if row is None:
        return None

    payload_json = row["payload_json"]
    if not isinstance(payload_json, str):
        return None

    return json.loads(payload_json)


def list_snapshots(conn: sqlite3.Connection, tab: str, limit: int = 10) -> list[dict]:
    """Return latest snapshot metadata rows for a tab."""
    rows = conn.execute(
        """
        SELECT id, created_at, status
        FROM snapshots
        WHERE tab = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (tab, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def get_snapshot_by_id(conn: sqlite3.Connection, snapshot_id: int) -> dict | None:
    """Return snapshot record with parsed payload by id."""
    row = conn.execute(
        """
        SELECT id, tab, created_at, status, payload_json
        FROM snapshots
        WHERE id = ?
        LIMIT 1
        """,
        (snapshot_id,),
    ).fetchone()

    if row is None:
        return None

    payload_json = row["payload_json"]
    payload = json.loads(payload_json) if isinstance(payload_json, str) else None

    return {
        "id": row["id"],
        "tab": row["tab"],
        "created_at": row["created_at"],
        "status": row["status"],
        "payload": payload,
    }


def list_audit(
    conn: sqlite3.Connection, tab: str | None = None, limit: int = 50
) -> list[dict]:
    """Return latest audit events optionally filtered by tab."""
    if tab:
        rows = conn.execute(
            """
            SELECT id, created_at, tab, action, detail
            FROM audit_log
            WHERE tab = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (tab, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT id, created_at, tab, action, detail
            FROM audit_log
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]
