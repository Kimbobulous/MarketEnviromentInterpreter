"""Base provider interfaces for market data adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod


class MarketDataProvider(ABC):
    """Provider contract for daily OHLC market data."""

    @abstractmethod
    def get_daily_ohlc(
        self,
        symbol: str,
        start: str | None = None,
        end: str | None = None,
    ) -> list[dict]:
        """Return daily OHLC rows for a symbol."""
