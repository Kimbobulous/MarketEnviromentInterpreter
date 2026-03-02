import sqlite3

import pytest

from backend import main
from backend.lib.db import connect, init_db
from backend.lib.snapshots import save_snapshot


def _error_payload(tab: str = "intraday") -> dict:
    return {
        "tab": tab,
        "last_updated": "2026-03-02T00:00:00+00:00",
        "panels": [{"status": "error"}],
        "conditional_sensitivity": ["x"],
        "summary": ["y"],
    }


def _audit_actions(db_path) -> list[str]:
    conn = sqlite3.connect(str(db_path))
    try:
        return [
            row[0]
            for row in conn.execute("SELECT action FROM audit_log ORDER BY id").fetchall()
        ]
    finally:
        conn.close()


def test_forced_fail_returns_last_good_when_available(tmp_path, monkeypatch):
    db_path = tmp_path / "fallback_good.db"
    monkeypatch.setenv("MEI_DB_PATH", str(db_path))

    baseline = main.get_intraday()

    monkeypatch.setenv("MEI_FORCE_FAIL_TAB", "intraday")
    recovered = main.get_intraday()

    assert recovered == baseline

    actions = _audit_actions(db_path)
    assert "build_failed" in actions
    assert "served_last_good" in actions


def test_forced_fail_raises_and_logs_when_no_last_good(tmp_path, monkeypatch):
    db_path = tmp_path / "fallback_none.db"
    monkeypatch.setenv("MEI_DB_PATH", str(db_path))
    monkeypatch.setenv("MEI_FORCE_FAIL_TAB", "intraday")

    with pytest.raises(RuntimeError, match="forced failure"):
        main.get_intraday()

    actions = _audit_actions(db_path)
    assert "build_failed" in actions
    assert "served_last_good" not in actions


def test_forced_fail_does_not_serve_error_snapshot(tmp_path, monkeypatch):
    db_path = tmp_path / "fallback_error_only.db"
    monkeypatch.setenv("MEI_DB_PATH", str(db_path))

    conn = connect(str(db_path))
    try:
        init_db(conn)
        save_snapshot(conn, tab="intraday", payload=_error_payload("intraday"))
    finally:
        conn.close()

    monkeypatch.setenv("MEI_FORCE_FAIL_TAB", "intraday")

    with pytest.raises(RuntimeError, match="forced failure"):
        main.get_intraday()

    actions = _audit_actions(db_path)
    assert actions.count("build_failed") >= 1
    assert "served_last_good" not in actions
