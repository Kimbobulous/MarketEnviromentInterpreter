import json

from backend import main
from backend.lib.db import connect, init_db
from backend.lib.snapshots import save_snapshot


def _payload(tab: str, status: str, stamp: str) -> dict:
    return {
        "tab": tab,
        "last_updated": stamp,
        "panels": [{"status": status}],
        "conditional_sensitivity": ["x"],
        "summary": ["y"],
    }


def test_snapshots_latest_returns_metadata_only(tmp_path, monkeypatch):
    db_path = tmp_path / "snapshot_endpoints.db"
    monkeypatch.setenv("MEI_DB_PATH", str(db_path))

    conn = connect(str(db_path))
    try:
        init_db(conn)
        save_snapshot(conn, "intraday", _payload("intraday", "ok", "2026-03-02T00:00:00+00:00"))
        save_snapshot(
            conn,
            "intraday",
            _payload("intraday", "partial", "2026-03-02T00:01:00+00:00"),
        )
    finally:
        conn.close()

    out = main.get_snapshots_latest(tab="intraday", limit=10)
    assert out["tab"] == "intraday"
    assert out["count"] == 2
    assert isinstance(out["snapshots"], list) and out["snapshots"]
    first = out["snapshots"][0]
    assert set(first.keys()) == {"id", "created_at", "status"}


def test_snapshot_by_id_returns_payload_and_404_when_missing(tmp_path, monkeypatch):
    db_path = tmp_path / "snapshot_by_id.db"
    monkeypatch.setenv("MEI_DB_PATH", str(db_path))

    conn = connect(str(db_path))
    try:
        init_db(conn)
        payload = _payload("intraday", "ok", "2026-03-02T00:02:00+00:00")
        snapshot_id = save_snapshot(conn, "intraday", payload)
    finally:
        conn.close()

    found = main.get_snapshot(snapshot_id=snapshot_id)
    assert found["id"] == snapshot_id
    assert found["tab"] == "intraday"
    assert found["status"] == "ok"
    assert found["payload"] == payload

    missing = main.get_snapshot(snapshot_id=999999)
    assert missing.status_code == 404
    assert json.loads(missing.body.decode("utf-8")) == {"error": "not found"}


def test_audit_endpoint_returns_events_with_snapshot_saved(tmp_path, monkeypatch):
    db_path = tmp_path / "audit_endpoint.db"
    monkeypatch.setenv("MEI_DB_PATH", str(db_path))

    conn = connect(str(db_path))
    try:
        init_db(conn)
        save_snapshot(conn, "intraday", _payload("intraday", "ok", "2026-03-02T00:03:00+00:00"))
        save_snapshot(conn, "swing", _payload("swing", "ok", "2026-03-02T00:04:00+00:00"))
    finally:
        conn.close()

    out = main.get_audit(limit=5)
    assert out["count"] >= 2
    assert isinstance(out["events"], list) and out["events"]
    assert "snapshot_saved" in {event["action"] for event in out["events"]}

    intraday_only = main.get_audit(tab="intraday", limit=5)
    assert intraday_only["events"]
    assert {event["tab"] for event in intraday_only["events"]} == {"intraday"}
