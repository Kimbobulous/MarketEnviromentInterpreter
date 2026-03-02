from pathlib import Path

import pytest

from backend.lib.db import connect, init_db
from backend.lib.market_data.client import daily_ohlc_cache_key
from backend.lib.market_data.cache import cache_get, cache_put
from backend.lib.market_data.fred_provider import FredProvider
from backend.lib.market_data.polygon_provider import PolygonProvider


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class _FakeResponse:
    def __init__(self, text: str):
        self._bytes = text.encode("utf-8")

    def read(self):
        return self._bytes

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_polygon_provider_parses_rows_and_dates(monkeypatch):
    payload = (FIXTURES_DIR / "polygon_spy_aggs.json").read_text(encoding="utf-8")
    seen = {"url": ""}

    def _fake_urlopen(url, timeout=15):
        seen["url"] = url
        return _FakeResponse(payload)

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    provider = PolygonProvider(api_key="test-key")
    rows = provider.get_daily_ohlc("SPY", start="2024-01-02", end="2024-01-04")

    assert "api.polygon.io" in seen["url"]
    assert "SPY" in seen["url"]
    assert len(rows) == 3
    assert rows[0]["date"] == "2024-01-02"
    assert rows[0]["open"] == 470.0
    assert rows[0]["close"] == 471.2


@pytest.mark.parametrize(
    ("symbol", "fixture_name"),
    [
        ("RSP", "polygon_rsp_aggs.json"),
        ("QQQ", "polygon_qqq_aggs.json"),
        ("HYG", "polygon_hyg_aggs.json"),
        ("SHY", "polygon_shy_aggs.json"),
        ("VXX", "polygon_vxx_aggs.json"),
    ],
)
def test_polygon_provider_parses_generic_etf_tickers(monkeypatch, symbol, fixture_name):
    payload = (FIXTURES_DIR / fixture_name).read_text(encoding="utf-8")
    seen = {"url": ""}

    def _fake_urlopen(url, timeout=15):
        _ = timeout
        seen["url"] = url
        return _FakeResponse(payload)

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    provider = PolygonProvider(api_key="test-key")
    rows = provider.get_daily_ohlc(symbol, start="2024-01-02", end="2024-01-04")

    assert symbol in seen["url"]
    assert len(rows) == 3
    assert rows[0]["date"] == "2024-01-02"
    assert isinstance(rows[0]["close"], float)


def test_fred_provider_parses_rows_and_skips_missing_values(monkeypatch):
    payload = (FIXTURES_DIR / "fred_dgs10.json").read_text(encoding="utf-8")

    def _fake_urlopen(url, timeout=15):
        assert "series_id=DGS10" in url
        return _FakeResponse(payload)

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    provider = FredProvider(api_key="fred-key")
    rows = provider.get_daily_series("DGS10", start="2024-01-01", end="2024-01-10")

    assert rows == [
        {"date": "2024-01-02", "value": 3.95},
        {"date": "2024-01-04", "value": 4.01},
    ]


def test_market_cache_get_put_round_trip(tmp_path):
    db_path = tmp_path / "cache.db"
    conn = connect(str(db_path))
    try:
        init_db(conn)
        key = "polygon:ohlc:SPY:2024-01-01:2024-12-31"
        rows = [{"date": "2024-01-02", "close": 470.5}]

        cache_put(conn, key=key, rows=rows)
        cached = cache_get(conn, key=key, max_age_seconds=3600)
    finally:
        conn.close()

    assert cached == rows


def test_daily_ohlc_cache_key_includes_ticker_and_date_range():
    key_rsp = daily_ohlc_cache_key("RSP", start="2024-01-01", end="2024-12-31")
    key_qqq = daily_ohlc_cache_key("QQQ", start="2024-01-01", end="2024-12-31")

    assert key_rsp == "polygon:ohlc:RSP:2024-01-01:2024-12-31"
    assert key_qqq == "polygon:ohlc:QQQ:2024-01-01:2024-12-31"
    assert key_rsp != key_qqq
