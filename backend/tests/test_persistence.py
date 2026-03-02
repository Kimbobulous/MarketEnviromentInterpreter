import sqlite3

from backend import main
from backend.lib.db import connect, init_db
from backend.lib.snapshots import (
    derive_payload_status,
    get_last_good_snapshot,
    save_snapshot,
)


def _sample_payload(statuses):
    return {
        "tab": "intraday",
        "last_updated": "2026-03-02T00:00:00+00:00",
        "panels": [{"status": status} for status in statuses],
        "conditional_sensitivity": ["a"],
        "summary": ["b"],
    }


def test_init_db_creates_required_tables(tmp_path):
    db_path = tmp_path / "test.db"
    conn = connect(str(db_path))
    try:
        init_db(conn)
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    finally:
        conn.close()

    table_names = {row["name"] for row in rows}
    assert "snapshots" in table_names
    assert "audit_log" in table_names


def test_derive_payload_status_rules():
    assert derive_payload_status(_sample_payload(["ok", "ok"])) == "ok"
    assert derive_payload_status(_sample_payload(["ok", "partial"])) == "partial"
    assert derive_payload_status(_sample_payload(["partial", "error"])) == "error"


def test_save_snapshot_and_get_last_good_round_trip(tmp_path):
    db_path = tmp_path / "snapshots.db"
    conn = connect(str(db_path))
    try:
        init_db(conn)
        payload_ok = _sample_payload(["ok"])
        snapshot_id = save_snapshot(conn, tab="intraday", payload=payload_ok)
        assert snapshot_id > 0

        payload_error = _sample_payload(["error"])
        save_snapshot(conn, tab="intraday", payload=payload_error)

        last_good = get_last_good_snapshot(conn, tab="intraday")
    finally:
        conn.close()

    assert last_good == payload_ok


def test_save_snapshot_and_get_last_good_round_trip_for_swing(tmp_path):
    db_path = tmp_path / "swing_snapshots.db"
    conn = connect(str(db_path))
    try:
        init_db(conn)
        payload_ok = {**_sample_payload(["ok"]), "tab": "swing"}
        snapshot_id = save_snapshot(conn, tab="swing", payload=payload_ok)
        assert snapshot_id > 0

        payload_error = {**_sample_payload(["error"]), "tab": "swing"}
        save_snapshot(conn, tab="swing", payload=payload_error)

        last_good = get_last_good_snapshot(conn, tab="swing")
    finally:
        conn.close()

    assert last_good == payload_ok


def test_intraday_endpoint_saves_snapshot(tmp_path, monkeypatch):
    db_path = tmp_path / "intraday.db"
    monkeypatch.setenv("MEI_DB_PATH", str(db_path))

    payload = main.get_intraday()
    assert payload["tab"] == "intraday"

    conn = sqlite3.connect(str(db_path))
    try:
        count = conn.execute("SELECT count(*) FROM snapshots").fetchone()[0]
    finally:
        conn.close()

    assert count >= 1


def test_swing_endpoint_saves_snapshot_and_increments_count(tmp_path, monkeypatch):
    db_path = tmp_path / "swing_endpoint.db"
    monkeypatch.setenv("MEI_DB_PATH", str(db_path))

    first_payload = main.get_swing()
    second_payload = main.get_swing()
    assert first_payload["tab"] == "swing"
    assert second_payload["tab"] == "swing"
    assert set(first_payload.keys()) == {
        "tab",
        "last_updated",
        "panels",
        "conditional_sensitivity",
        "summary",
    }
    assert set(second_payload.keys()) == set(first_payload.keys())

    conn = sqlite3.connect(str(db_path))
    try:
        count = conn.execute(
            "SELECT count(*) FROM snapshots WHERE tab='swing'"
        ).fetchone()[0]
    finally:
        conn.close()

    assert count >= 2


def test_intraday_uses_last_good_snapshot_when_build_fails(tmp_path, monkeypatch):
    db_path = tmp_path / "fallback.db"
    monkeypatch.setenv("MEI_DB_PATH", str(db_path))

    baseline = main.get_intraday()

    def _boom(*_args, **_kwargs):
        raise RuntimeError("forced build failure")

    monkeypatch.setattr(main, "build_payload", _boom)

    recovered = main.get_intraday()
    assert recovered == baseline

    conn = sqlite3.connect(str(db_path))
    try:
        actions = [
            row[0]
            for row in conn.execute(
                "SELECT action FROM audit_log ORDER BY id"
            ).fetchall()
        ]
    finally:
        conn.close()

    assert "build_failed" in actions
    assert "served_last_good" in actions
