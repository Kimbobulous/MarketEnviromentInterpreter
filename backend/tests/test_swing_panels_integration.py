from datetime import date, timedelta
import math
import re
import urllib.request

from backend import main
from backend.lib.interpret import BANNED_PHRASES


TOP_LEVEL_KEYS = {
    "tab",
    "last_updated",
    "panels",
    "conditional_sensitivity",
    "summary",
}

PANEL_KEYS = {
    "id",
    "title",
    "raw_metrics",
    "sparkline",
    "sparkline_times",
    "context",
    "interpretation",
    "why_toggle",
    "status",
    "last_updated",
}

WINDOW_META_KEYS = {
    "series_points",
    "series_target",
    "series_min",
    "pctl_lookback",
    "trend_lookback",
    "pctl_excludes_current",
}

REQUIRED_RAW_METRIC_KEYS = {
    "latest",
    "percentile_lookback",
    "regime",
    "trend_slope",
    "trend_direction",
    "source_tickers",
}


def _assert_no_banned_phrases(text: str):
    lowered = f" {text.lower()} "
    for phrase in BANNED_PHRASES:
        assert phrase.lower() not in lowered


def _business_dates(n: int) -> list[str]:
    out: list[str] = []
    cursor = date(2024, 1, 2)
    while len(out) < n:
        if cursor.weekday() < 5:
            out.append(cursor.isoformat())
        cursor += timedelta(days=1)
    return out


def _daily_rows(
    base: float,
    step: float,
    amplitude: float,
    phase: float,
    n: int = 340,
):
    rows = []
    dates = _business_dates(n)
    for i, row_date in enumerate(dates):
        close = base + (step * i) + (amplitude * math.sin((i + phase) / 9.0))
        rows.append(
            {
                "date": row_date,
                "open": close - 0.05,
                "high": close + 0.1,
                "low": close - 0.1,
                "close": close,
                "volume": 500000 + i,
            }
        )
    return rows


def _set_last_close(rows: list[dict], source_index: int) -> None:
    value = float(rows[source_index]["close"])
    rows[-1]["close"] = value
    rows[-1]["open"] = value - 0.05
    rows[-1]["high"] = value + 0.1
    rows[-1]["low"] = value - 0.1


def test_swing_panels_use_computed_proxy_metrics_and_guardrails(monkeypatch):
    ticker_rows = {
        "RSP": _daily_rows(160.0, 0.08, 2.0, 0.0),
        "SPY": _daily_rows(470.0, 0.12, 3.0, 2.0),
        "QQQ": _daily_rows(390.0, 0.15, 3.5, 5.0),
        "HYG": _daily_rows(75.0, 0.02, 0.5, 1.0),
        "SHY": _daily_rows(82.0, 0.004, 0.2, 4.0),
        "VXX": _daily_rows(20.0, -0.01, 0.7, 7.0),
        "I:VIX": _daily_rows(14.0, 0.01, 0.8, 3.0),
    }
    _set_last_close(ticker_rows["RSP"], -90)
    _set_last_close(ticker_rows["HYG"], -120)

    def _fake_get_daily_ohlc(_conn, symbol, start=None, end=None):
        _ = (start, end)
        rows = ticker_rows.get(symbol)
        if rows is None:
            raise RuntimeError(f"No rows returned from provider for {symbol}")
        return rows

    def _no_network(*_args, **_kwargs):
        raise AssertionError("network call not expected in swing integration test")

    monkeypatch.setattr(main, "get_daily_ohlc", _fake_get_daily_ohlc)
    monkeypatch.setattr(urllib.request, "urlopen", _no_network)

    payload = main.get_swing()

    assert set(payload.keys()) == TOP_LEVEL_KEYS
    assert payload["tab"] == "swing"
    assert isinstance(payload["panels"], list)
    assert len(payload["panels"]) >= 4

    percentiles: list[float] = []
    for panel in payload["panels"]:
        assert PANEL_KEYS <= set(panel.keys())
        assert panel["status"] == "ok"
        assert isinstance(panel["sparkline"], list)
        assert isinstance(panel["sparkline_times"], list)
        assert len(panel["sparkline_times"]) == len(panel["sparkline"])
        assert len(panel["sparkline_times"]) <= 60
        assert len(panel["sparkline"]) <= 60
        assert all(isinstance(value, (int, float)) for value in panel["sparkline"])
        assert all(isinstance(value, str) for value in panel["sparkline_times"])
        assert all(re.match(r"^\d{4}-\d{2}-\d{2}$", value) for value in panel["sparkline_times"])
        assert WINDOW_META_KEYS <= set(panel.get("window_meta", {}).keys())

        metric_keys = {metric.get("key") for metric in panel["raw_metrics"]}
        assert REQUIRED_RAW_METRIC_KEYS <= metric_keys
        metric_map = {metric.get("key"): metric.get("value") for metric in panel["raw_metrics"]}
        percentile = metric_map.get("percentile_lookback")
        if isinstance(percentile, (int, float)):
            percentiles.append(float(percentile))

        for line in panel["context"]:
            _assert_no_banned_phrases(line)
        for line in panel["interpretation"]:
            _assert_no_banned_phrases(line)
        if isinstance(panel["why_toggle"], list):
            for line in panel["why_toggle"]:
                _assert_no_banned_phrases(line)
        else:
            _assert_no_banned_phrases(panel["why_toggle"])

    assert percentiles
    assert any(0.0 < percentile < 100.0 for percentile in percentiles)
    assert not all(percentile in {0.0, 100.0} for percentile in percentiles)
