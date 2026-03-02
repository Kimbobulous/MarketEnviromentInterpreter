from datetime import date, timedelta

from backend import main


def _date_rows(n: int) -> list[str]:
    out: list[str] = []
    cursor = date(2024, 1, 2)
    while len(out) < n:
        out.append(cursor.isoformat())
        cursor += timedelta(days=1)
    return out


def _monotonic_close_rows(
    start: float,
    step: float,
    n: int = 520,
    repeat: int = 3,
) -> list[dict]:
    rows: list[dict] = []
    dates = _date_rows(n)
    for i, row_date in enumerate(dates):
        level = i // repeat
        close = start + (step * level)
        rows.append(
            {
                "date": row_date,
                "open": close - 0.1,
                "high": close + 0.2,
                "low": close - 0.2,
                "close": close,
                "volume": 1000000 + i,
            }
        )
    return rows


def _monotonic_value_rows(
    start: float,
    step: float,
    n: int = 520,
    repeat: int = 3,
) -> list[dict]:
    rows: list[dict] = []
    dates = _date_rows(n)
    for i, row_date in enumerate(dates):
        level = i // repeat
        value = start + (step * level)
        rows.append({"date": row_date, "value": value})
    return rows


def test_percentile_sanity_endpoint_responds_and_includes_required_fields(monkeypatch):
    spy_rows = _monotonic_close_rows(start=400.0, step=0.4, repeat=3)
    vxx_rows = _monotonic_close_rows(start=20.0, step=0.03, repeat=4)
    dgs10_rows = _monotonic_value_rows(start=2.0, step=0.01, repeat=3)

    monkeypatch.setenv("MEI_VIX_PROXY_TICKER", "VXX")
    monkeypatch.setattr(main, "get_spy_daily", lambda conn: spy_rows)
    monkeypatch.setattr(main, "get_yield_daily", lambda conn: dgs10_rows)
    monkeypatch.setattr(
        main,
        "get_daily_ohlc",
        lambda conn, symbol, start=None, end=None: vxx_rows,
    )

    payload = main.get_percentile_sanity()
    assert payload["percentile_excludes_current"] is True
    assert payload["lookbacks"] == [126, 252]
    assert "series" in payload

    required_summary_keys = {
        "lookback",
        "sample_size_available",
        "computed_percentiles",
        "sample_size_window",
        "sample_window",
        "min",
        "max",
        "mean",
        "count_le_5",
        "count_ge_95",
        "count_eq_0",
        "count_eq_100",
    }

    for series_key in ["spy", "vxx", "dgs10"]:
        series_block = payload["series"][series_key]
        assert "sample_size_available" in series_block
        assert "lookback_summaries" in series_block

        lookbacks = series_block["lookback_summaries"]
        assert "126" in lookbacks
        assert "252" in lookbacks

        for key in ["126", "252"]:
            assert required_summary_keys <= set(lookbacks[key].keys())


def test_percentile_sanity_monotonic_series_not_pathological_on_exact_extremes(monkeypatch):
    spy_rows = _monotonic_close_rows(start=300.0, step=0.2, repeat=3)
    vxx_rows = _monotonic_close_rows(start=18.0, step=0.02, repeat=3)
    dgs10_rows = _monotonic_value_rows(start=1.8, step=0.008, repeat=3)

    monkeypatch.setenv("MEI_VIX_PROXY_TICKER", "VXX")
    monkeypatch.setattr(main, "get_spy_daily", lambda conn: spy_rows)
    monkeypatch.setattr(main, "get_yield_daily", lambda conn: dgs10_rows)
    monkeypatch.setattr(
        main,
        "get_daily_ohlc",
        lambda conn, symbol, start=None, end=None: vxx_rows,
    )

    payload = main.get_percentile_sanity()

    for series_key in ["spy", "vxx", "dgs10"]:
        lookbacks = payload["series"][series_key]["lookback_summaries"]
        for lookback_key in ["126", "252"]:
            summary = lookbacks[lookback_key]
            sample_count = summary["sample_size_window"]
            assert sample_count > 0
            assert summary["count_eq_0"] == 0
            assert summary["count_eq_100"] < sample_count
