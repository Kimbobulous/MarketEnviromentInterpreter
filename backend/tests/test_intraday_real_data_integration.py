from datetime import date, timedelta
import math
import re
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

COMPUTE_METRIC_KEYS = {
    "percentile_lookback",
    "regime",
    "trend_slope",
    "trend_direction",
}


def _business_dates(n: int) -> list[str]:
    out: list[str] = []
    cursor = date(2024, 1, 2)
    while len(out) < n:
        if cursor.weekday() < 5:
            out.append(cursor.isoformat())
        cursor += timedelta(days=1)
    return out


def _series_rows(
    key: str,
    base: float,
    step: float,
    amplitude: float,
    phase: float = 0.0,
    n: int = 320,
):
    rows = []
    dates = _business_dates(n)
    for i, row_date in enumerate(dates):
        value = base + (step * i) + (amplitude * math.sin((i + phase) / 11.0))
        rows.append({"date": row_date, key: value})
    return rows


def test_intraday_real_data_payload_contract_with_mocked_client(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_spy_daily",
        lambda conn: _series_rows("close", base=400.0, step=0.2, amplitude=2.5, phase=0.0),
    )
    monkeypatch.setattr(
        main,
        "get_vix_daily",
        lambda conn: _series_rows("close", base=15.0, step=0.01, amplitude=1.2, phase=3.0),
    )
    monkeypatch.setattr(
        main,
        "get_yield_daily",
        lambda conn: _series_rows("value", base=3.5, step=0.001, amplitude=0.06, phase=7.0),
    )

    def _no_network(*_args, **_kwargs):
        raise AssertionError("network call not expected in this test")

    monkeypatch.setattr(urllib.request, "urlopen", _no_network)

    payload = main.get_intraday()

    assert set(payload.keys()) == TOP_LEVEL_KEYS
    assert payload["tab"] == "intraday"
    assert isinstance(payload["panels"], list)
    assert len(payload["panels"]) >= 3

    percentiles: list[float] = []
    for panel in payload["panels"]:
        assert PANEL_KEYS <= set(panel.keys())
        assert panel["status"] == "ok"
        metric_keys = {metric.get("key") for metric in panel["raw_metrics"]}
        assert COMPUTE_METRIC_KEYS <= metric_keys
        assert isinstance(panel["sparkline"], list)
        assert isinstance(panel["sparkline_times"], list)
        assert len(panel["sparkline_times"]) == len(panel["sparkline"])
        assert len(panel["sparkline_times"]) <= 60
        assert len(panel["sparkline"]) <= 60
        assert all(isinstance(value, (int, float)) for value in panel["sparkline"])
        assert all(isinstance(value, str) for value in panel["sparkline_times"])
        assert all(re.match(r"^\d{4}-\d{2}-\d{2}$", value) for value in panel["sparkline_times"])
        assert WINDOW_META_KEYS <= set(panel.get("window_meta", {}).keys())

        metric_map = {metric.get("key"): metric.get("value") for metric in panel["raw_metrics"]}
        percentile = metric_map.get("percentile_lookback")
        if isinstance(percentile, (int, float)):
            percentiles.append(float(percentile))

    assert percentiles
    assert any(0.0 < percentile < 100.0 for percentile in percentiles)
    assert not all(percentile in {0.0, 100.0} for percentile in percentiles)
