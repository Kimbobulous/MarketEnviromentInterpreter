import sqlite3
import urllib.error
import urllib.request

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


def _ok_payload(tab: str = "intraday") -> dict:
    return {
        "tab": tab,
        "last_updated": "2026-03-02T00:05:00+00:00",
        "panels": [{"status": "ok"}],
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


def _audit_actions_for_tab(db_path, tab: str) -> list[str]:
    conn = sqlite3.connect(str(db_path))
    try:
        return [
            row[0]
            for row in conn.execute(
                "SELECT action FROM audit_log WHERE tab = ? ORDER BY id",
                (tab,),
            ).fetchall()
        ]
    finally:
        conn.close()


def _swing_rows(base: float, step: float, n: int = 120) -> list[dict]:
    rows = []
    for i in range(n):
        rows.append(
            {
                "date": f"2025-04-{(i % 28) + 1:02d}",
                "open": base + (step * i) - 0.05,
                "high": base + (step * i) + 0.1,
                "low": base + (step * i) - 0.1,
                "close": base + (step * i),
                "volume": 900000 + i,
            }
        )
    return rows


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


@pytest.mark.use_provider_path
def test_provider_failure_serves_last_good_and_logs_audit(tmp_path, monkeypatch):
    db_path = tmp_path / "provider_fallback.db"
    monkeypatch.setenv("MEI_DB_PATH", str(db_path))
    monkeypatch.setenv("MEI_POLYGON_API_KEY", "test-polygon")
    monkeypatch.setenv("MEI_FRED_API_KEY", "test-fred")
    monkeypatch.delenv("MEI_FORCE_FAIL_TAB", raising=False)

    conn = connect(str(db_path))
    try:
        init_db(conn)
        baseline = _ok_payload("intraday")
        save_snapshot(conn, tab="intraday", payload=baseline)
    finally:
        conn.close()

    def _raise_provider_error(*_args, **_kwargs):
        raise urllib.error.URLError("provider unavailable")

    monkeypatch.setattr(urllib.request, "urlopen", _raise_provider_error)

    recovered = main.get_intraday()
    assert recovered == baseline

    actions = _audit_actions(db_path)
    assert "build_failed" in actions
    assert "served_last_good" in actions


@pytest.mark.use_provider_path
def test_swing_provider_failure_serves_last_good_and_logs_audit(tmp_path, monkeypatch):
    db_path = tmp_path / "swing_provider_fallback.db"
    monkeypatch.setenv("MEI_DB_PATH", str(db_path))
    monkeypatch.setenv("MEI_POLYGON_API_KEY", "test-polygon")
    monkeypatch.delenv("MEI_FORCE_FAIL_TAB", raising=False)

    rows_by_ticker = {
        "RSP": _swing_rows(160.0, 0.08),
        "SPY": _swing_rows(470.0, 0.12),
        "QQQ": _swing_rows(390.0, 0.16),
        "HYG": _swing_rows(75.0, 0.02),
        "SHY": _swing_rows(82.0, 0.005),
        "VXX": _swing_rows(20.0, -0.01),
        "I:VIX": _swing_rows(14.0, 0.01),
    }

    original_get_daily_ohlc = main.get_daily_ohlc

    def _mock_good_swing_data(_conn, symbol, start=None, end=None):
        _ = (start, end)
        rows = rows_by_ticker.get(symbol)
        if rows is None:
            raise RuntimeError(f"No rows returned from provider for {symbol}")
        return rows

    monkeypatch.setattr(main, "get_daily_ohlc", _mock_good_swing_data)
    baseline = main.get_swing()

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("DELETE FROM market_cache")
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setattr(main, "get_daily_ohlc", original_get_daily_ohlc)

    def _raise_provider_error(*_args, **_kwargs):
        raise urllib.error.URLError("provider unavailable")

    monkeypatch.setattr(urllib.request, "urlopen", _raise_provider_error)

    recovered = main.get_swing()
    assert recovered == baseline

    swing_actions = _audit_actions_for_tab(db_path, "swing")
    assert "build_failed" in swing_actions
    assert "served_last_good" in swing_actions
