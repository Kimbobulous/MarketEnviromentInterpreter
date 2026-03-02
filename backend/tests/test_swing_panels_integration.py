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
    "context",
    "interpretation",
    "why_toggle",
    "status",
    "last_updated",
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


def _daily_rows(base: float, step: float, n: int = 140):
    rows = []
    for i in range(n):
        rows.append(
            {
                "date": f"2025-03-{(i % 28) + 1:02d}",
                "open": base + (step * i) - 0.05,
                "high": base + (step * i) + 0.1,
                "low": base + (step * i) - 0.1,
                "close": base + (step * i),
                "volume": 500000 + i,
            }
        )
    return rows


def test_swing_panels_use_computed_proxy_metrics_and_guardrails(monkeypatch):
    ticker_rows = {
        "RSP": _daily_rows(160.0, 0.08),
        "SPY": _daily_rows(470.0, 0.12),
        "QQQ": _daily_rows(390.0, 0.15),
        "HYG": _daily_rows(75.0, 0.02),
        "SHY": _daily_rows(82.0, 0.004),
        "VXX": _daily_rows(20.0, -0.01),
        "I:VIX": _daily_rows(14.0, 0.01),
    }

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

    for panel in payload["panels"]:
        assert set(panel.keys()) == PANEL_KEYS
        assert panel["status"] in {"ok", "partial", "error"}

        metric_keys = {metric.get("key") for metric in panel["raw_metrics"]}
        assert REQUIRED_RAW_METRIC_KEYS <= metric_keys

        for line in panel["context"]:
            _assert_no_banned_phrases(line)
        for line in panel["interpretation"]:
            _assert_no_banned_phrases(line)
        if isinstance(panel["why_toggle"], list):
            for line in panel["why_toggle"]:
                _assert_no_banned_phrases(line)
        else:
            _assert_no_banned_phrases(panel["why_toggle"])
