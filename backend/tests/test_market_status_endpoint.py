from backend import main
from backend.lib.db import connect, init_db
from backend.lib.market_data.cache import cache_put
from backend.lib.market_data.client import spy_cache_key, vix_cache_key, yield_cache_key


def test_market_status_endpoint_reports_cache_metadata(tmp_path, monkeypatch):
    db_path = tmp_path / "market_status.db"
    monkeypatch.setenv("MEI_DB_PATH", str(db_path))
    monkeypatch.setenv("MEI_MARKET_CACHE_MAX_AGE_SECONDS", "3600")

    conn = connect(str(db_path))
    try:
        init_db(conn)
        cache_put(conn, spy_cache_key(), rows=[{"date": "2025-01-02", "close": 470.0}] * 3)
        cache_put(conn, vix_cache_key(), rows=[{"date": "2025-01-02", "close": 14.2}] * 2)
        cache_put(conn, yield_cache_key(), rows=[{"date": "2025-01-02", "value": 3.9}] * 4)
    finally:
        conn.close()

    out = main.get_market_status()

    assert "sources" in out
    assert set(out["sources"].keys()) == {"spy", "vix", "yield"}

    spy = out["sources"]["spy"]
    vix = out["sources"]["vix"]
    yld = out["sources"]["yield"]

    assert spy["provider"] == "polygon"
    assert vix["provider"] == "polygon"
    assert yld["provider"] == "fred"

    assert spy["rows"] == 3
    assert vix["rows"] == 2
    assert yld["rows"] == 4

    for source in (spy, vix, yld):
        assert source["cached"] is True
        assert isinstance(source["age_seconds"], int)
        assert source["age_seconds"] >= 0
        assert isinstance(source["fetched_at"], str) and source["fetched_at"]
