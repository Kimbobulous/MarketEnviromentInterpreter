import pytest

from backend import main


def _series_rows(key: str, base: float, step: float, n: int = 90):
    return [
        {"date": f"2025-01-{(i % 28) + 1:02d}", key: base + (step * i)}
        for i in range(n)
    ]


@pytest.fixture(autouse=True)
def _stub_intraday_market_data(monkeypatch, request):
    if request.node.get_closest_marker("use_provider_path"):
        return

    monkeypatch.setattr(main, "get_spy_daily", lambda conn: _series_rows("close", 400.0, 0.5))
    monkeypatch.setattr(main, "get_vix_daily", lambda conn: _series_rows("close", 12.0, 0.05))
    monkeypatch.setattr(main, "get_yield_daily", lambda conn: _series_rows("value", 3.0, 0.01))
