import pytest

from backend import main


def _series_rows(key: str, base: float, step: float, n: int = 90):
    return [
        {"date": f"2025-01-{(i % 28) + 1:02d}", key: base + (step * i)}
        for i in range(n)
    ]


def _ticker_close_rows(base: float, step: float, n: int = 120):
    rows = []
    for i in range(n):
        rows.append(
            {
                "date": f"2025-02-{(i % 28) + 1:02d}",
                "open": base + (step * i) - 0.1,
                "high": base + (step * i) + 0.2,
                "low": base + (step * i) - 0.2,
                "close": base + (step * i),
                "volume": 1000000 + i,
            }
        )
    return rows


@pytest.fixture(autouse=True)
def _stub_intraday_market_data(monkeypatch, request):
    if request.node.get_closest_marker("use_provider_path"):
        return

    monkeypatch.setattr(main, "get_spy_daily", lambda conn: _series_rows("close", 400.0, 0.5))
    monkeypatch.setattr(main, "get_vix_daily", lambda conn: _series_rows("close", 12.0, 0.05))
    monkeypatch.setattr(main, "get_yield_daily", lambda conn: _series_rows("value", 3.0, 0.01))

    ticker_map = {
        "RSP": _ticker_close_rows(160.0, 0.08),
        "SPY": _ticker_close_rows(470.0, 0.12),
        "QQQ": _ticker_close_rows(390.0, 0.16),
        "HYG": _ticker_close_rows(75.0, 0.02),
        "SHY": _ticker_close_rows(82.0, 0.005),
        "VXX": _ticker_close_rows(20.0, -0.01),
        "I:VIX": _ticker_close_rows(14.0, 0.01),
    }

    def _swing_daily(_conn, symbol, start=None, end=None):
        _ = (start, end)
        rows = ticker_map.get(symbol)
        if rows is None:
            raise RuntimeError(f"No rows returned from provider for {symbol}")
        return rows

    monkeypatch.setattr(main, "get_daily_ohlc", _swing_daily)
