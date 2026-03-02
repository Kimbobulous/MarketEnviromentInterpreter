"""FRED provider for daily macro series observations."""

from __future__ import annotations

from datetime import date, timedelta
import json
import urllib.parse
import urllib.request


class FredProvider:
    """Fetch FRED observations for configured series."""

    BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_daily_series(
        self,
        series_id: str,
        start: str | None = None,
        end: str | None = None,
    ) -> list[dict]:
        if not self.api_key:
            raise RuntimeError("MEI_FRED_API_KEY is required")

        start_date, end_date = _resolve_date_range(start=start, end=end)

        params = urllib.parse.urlencode(
            {
                "series_id": series_id,
                "api_key": self.api_key,
                "file_type": "json",
                "observation_start": start_date,
                "observation_end": end_date,
            }
        )
        url = f"{self.BASE_URL}?{params}"

        payload = _read_json(url)
        observations = (
            payload.get("observations", []) if isinstance(payload, dict) else []
        )

        rows = []
        for obs in observations:
            if not isinstance(obs, dict):
                continue

            obs_date = obs.get("date")
            raw_value = obs.get("value")
            if not isinstance(obs_date, str) or raw_value in {None, "."}:
                continue

            try:
                numeric_value = float(raw_value)
            except (TypeError, ValueError):
                continue

            rows.append({"date": obs_date, "value": numeric_value})

        return rows


def _resolve_date_range(start: str | None, end: str | None) -> tuple[str, str]:
    end_date = end or date.today().isoformat()
    if start:
        return start, end_date

    default_start = (date.today() - timedelta(days=400)).isoformat()
    return default_start, end_date


def _read_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=15) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw)
