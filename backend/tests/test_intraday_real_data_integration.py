import urllib.request

from backend import main


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

COMPUTE_METRIC_KEYS = {
    "percentile_lookback",
    "regime",
    "trend_slope",
    "trend_direction",
}


def _series_rows(key: str, base: float, step: float, n: int = 90):
    rows = []
    for i in range(n):
        rows.append({"date": f"2025-01-{(i % 28) + 1:02d}", key: base + (step * i)})
    return rows


def test_intraday_real_data_payload_contract_with_mocked_client(monkeypatch):
    monkeypatch.setattr(main, "get_spy_daily", lambda conn: _series_rows("close", 400.0, 0.5))
    monkeypatch.setattr(main, "get_vix_daily", lambda conn: _series_rows("close", 12.0, 0.05))
    monkeypatch.setattr(main, "get_yield_daily", lambda conn: _series_rows("value", 3.0, 0.01))

    def _no_network(*_args, **_kwargs):
        raise AssertionError("network call not expected in this test")

    monkeypatch.setattr(urllib.request, "urlopen", _no_network)

    payload = main.get_intraday()

    assert set(payload.keys()) == TOP_LEVEL_KEYS
    assert payload["tab"] == "intraday"
    assert isinstance(payload["panels"], list)
    assert len(payload["panels"]) >= 3

    for panel in payload["panels"]:
        assert set(panel.keys()) == PANEL_KEYS
        assert panel["status"] in {"ok", "partial", "error"}
        metric_keys = {metric.get("key") for metric in panel["raw_metrics"]}
        assert COMPUTE_METRIC_KEYS <= metric_keys
