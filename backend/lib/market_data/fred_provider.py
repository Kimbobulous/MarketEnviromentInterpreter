"""FRED provider for daily macro series observations."""

from __future__ import annotations

from datetime import date, timedelta
import json
import urllib.error
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
        limit: int | None = None,
    ) -> list[dict]:
        start_date, end_date = _resolve_date_range(start=start, end=end)
        requested_limit = _resolve_limit(limit=limit, default=400)

        query = {
            "series_id": series_id,
            "file_type": "json",
            "observation_start": start_date,
            "observation_end": end_date,
            "sort_order": "asc",
            "limit": str(requested_limit),
        }
        if self.api_key:
            query["api_key"] = self.api_key
        params = urllib.parse.urlencode(query)
        url = f"{self.BASE_URL}?{params}"

        try:
            payload = _read_json(url)
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8")
            except Exception:
                body = ""
            if not self.api_key and exc.code in {400, 401, 403}:
                raise RuntimeError(
                    "FRED request rejected without API key; set MEI_FRED_API_KEY"
                ) from exc
            message = body.strip() or str(exc.reason or "")
            reason = message[:240] if message else f"http_status={exc.code}"
            raise RuntimeError(f"FRED request failed for {series_id}: {reason}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"FRED request failed for {series_id}: {exc.reason or str(exc)}"
            ) from exc
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

        rows.sort(key=lambda row: row.get("date", ""))
        if len(rows) > requested_limit:
            rows = rows[-requested_limit:]
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
    return max(1, min(parsed, 100_000))


def _read_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=15) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw)
