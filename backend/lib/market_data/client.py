"""Market-data client functions with SQLite caching."""

from __future__ import annotations

from datetime import date, timedelta
import os
import sqlite3

from backend.lib.market_data.cache import cache_get, cache_put
from backend.lib.market_data.fred_provider import FredProvider
from backend.lib.market_data.polygon_provider import PolygonProvider


def get_daily_ohlc(
    conn: sqlite3.Connection,
    symbol: str,
    start: str | None = None,
    end: str | None = None,
) -> list[dict]:
    """Return cached/fresh Polygon daily OHLC rows for any ticker."""
    provider = PolygonProvider(api_key=os.getenv("MEI_POLYGON_API_KEY", ""))
    start_date, end_date = _resolve_date_range(start=start, end=end)
    key = daily_ohlc_cache_key(symbol=symbol, start=start_date, end=end_date)
    max_age_seconds = _cache_max_age_seconds()

    cached = cache_get(conn, key=key, max_age_seconds=max_age_seconds)
    if cached is not None:
        return cached

    rows = provider.get_daily_ohlc(symbol, start=start_date, end=end_date)
    if not rows:
        raise RuntimeError(f"No rows returned from provider for {symbol}")

    cache_put(conn, key=key, rows=rows)
    return rows


def get_spy_daily(
    conn: sqlite3.Connection,
    start: str | None = None,
    end: str | None = None,
) -> list[dict]:
    ticker = os.getenv("MEI_SPY_TICKER", "SPY")
    return get_daily_ohlc(conn, symbol=ticker, start=start, end=end)


def get_vix_daily(
    conn: sqlite3.Connection,
    start: str | None = None,
    end: str | None = None,
) -> list[dict]:
    ticker = os.getenv("MEI_VIX_TICKER", "I:VIX")
    return get_daily_ohlc(conn, symbol=ticker, start=start, end=end)


def get_yield_daily(
    conn: sqlite3.Connection,
    start: str | None = None,
    end: str | None = None,
) -> list[dict]:
    series_id = os.getenv("MEI_YIELD_SERIES", "DGS10")
    provider_name = "fred"
    provider = FredProvider(api_key=os.getenv("MEI_FRED_API_KEY", ""))
    start_date, end_date = _resolve_date_range(start=start, end=end)
    key = f"{provider_name}:series:{series_id}:{start_date}:{end_date}"
    max_age_seconds = _cache_max_age_seconds()

    cached = cache_get(conn, key=key, max_age_seconds=max_age_seconds)
    if cached is not None:
        return cached

    rows = provider.get_daily_series(series_id, start=start_date, end=end_date)
    if not rows:
        raise RuntimeError("No yield rows returned from provider")

    cache_put(conn, key=key, rows=rows)
    return rows


def spy_cache_key(start: str | None = None, end: str | None = None) -> str:
    ticker = os.getenv("MEI_SPY_TICKER", "SPY")
    return daily_ohlc_cache_key(symbol=ticker, start=start, end=end)


def vix_cache_key(start: str | None = None, end: str | None = None) -> str:
    ticker = os.getenv("MEI_VIX_TICKER", "I:VIX")
    return daily_ohlc_cache_key(symbol=ticker, start=start, end=end)


def daily_ohlc_cache_key(symbol: str, start: str | None = None, end: str | None = None) -> str:
    """Return cache key for Polygon daily OHLC."""
    start_date, end_date = _resolve_date_range(start=start, end=end)
    return f"polygon:ohlc:{symbol}:{start_date}:{end_date}"


def yield_cache_key(start: str | None = None, end: str | None = None) -> str:
    series_id = os.getenv("MEI_YIELD_SERIES", "DGS10")
    start_date, end_date = _resolve_date_range(start=start, end=end)
    return f"fred:series:{series_id}:{start_date}:{end_date}"


def _resolve_date_range(start: str | None, end: str | None) -> tuple[str, str]:
    end_date = end or date.today().isoformat()
    if start:
        return start, end_date

    default_start = (date.today() - timedelta(days=400)).isoformat()
    return default_start, end_date


def _cache_max_age_seconds() -> int:
    raw = os.getenv("MEI_MARKET_CACHE_MAX_AGE_SECONDS", "3600")
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        return 3600
    return max(0, parsed)
