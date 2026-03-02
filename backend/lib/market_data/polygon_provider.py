"""Polygon provider for daily OHLC aggregates."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
import urllib.parse
import urllib.request

from .base import MarketDataProvider


class PolygonProvider(MarketDataProvider):
    """Fetch daily aggregate bars from Polygon/Massive."""

    BASE_URL = "https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_daily_ohlc(
        self,
        symbol: str,
        start: str | None = None,
        end: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        if not self.api_key:
            raise RuntimeError("MEI_POLYGON_API_KEY is required")

        start_date, end_date = _resolve_date_range(start=start, end=end)
        requested_limit = _resolve_limit(limit=limit, default=300)
        ticker = urllib.parse.quote(symbol, safe=":")
        params = urllib.parse.urlencode(
            {
                "adjusted": "true",
                "sort": "asc",
                "limit": str(requested_limit),
                "apiKey": self.api_key,
            }
        )
        url = (
            self.BASE_URL.format(ticker=ticker, start=start_date, end=end_date)
            + "?"
            + params
        )

        payload = _read_json(url)
        results = payload.get("results", []) if isinstance(payload, dict) else []
        rows = []
        for item in results:
            if not isinstance(item, dict):
                continue

            timestamp_ms = item.get("t")
            if not isinstance(timestamp_ms, (int, float)):
                continue

            row_date = (
                datetime.fromtimestamp(float(timestamp_ms) / 1000.0, tz=timezone.utc)
                .date()
                .isoformat()
            )
            rows.append(
                {
                    "date": row_date,
                    "open": _as_float(item.get("o")),
                    "high": _as_float(item.get("h")),
                    "low": _as_float(item.get("l")),
                    "close": _as_float(item.get("c")),
                    "volume": _as_float(item.get("v")),
                }
            )

        rows.sort(key=lambda row: row.get("date", ""))
        return rows


def _resolve_date_range(start: str | None, end: str | None) -> tuple[str, str]:
    end_date = end or date.today().isoformat()
    if start:
        return start, end_date

    default_start = (date.today() - timedelta(days=400)).isoformat()
    return default_start, end_date


def _resolve_limit(limit: int | None, default: int) -> int:
    try:
        parsed = int(limit) if limit is not None else default
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(parsed, 50_000))


def _read_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=15) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw)


def _as_float(value):
    if isinstance(value, (int, float)):
        return float(value)
    return None
