from datetime import datetime, timezone
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.lib.compute import classify_regime, rolling_percentile, trend_slope
from backend.lib.db import connect, init_db
from backend.lib.env import load_dotenv
from backend.lib.interpret import (
    detect_tensions,
    extract_signals,
    generate_interpretation,
    guard_language,
)
from backend.lib.market_data.cache import get_cache_entry
from backend.lib.market_data.client import (
    get_spy_daily,
    get_vix_daily,
    get_yield_daily,
    spy_cache_key,
    vix_cache_key,
    yield_cache_key,
)
from backend.lib.snapshots import get_snapshot_by_id, list_audit, list_snapshots
from backend.lib.snapshots import get_last_good_snapshot, log_action, save_snapshot

BACKEND_DIR = os.path.dirname(__file__)
DOTENV_PATH = os.path.join(BACKEND_DIR, ".env")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _initialize_runtime()
    yield


app = FastAPI(lifespan=lifespan)

TENSION_LABEL_ORDER = [
    "High+Down",
    "High+Flat",
    "Mid+Down",
    "Low+Up",
    "Trend unavailable",
]

allow_origins = [
    "http://localhost:3000",
    "https://cautious-waffle-r44r6x5p4g5v2p79w-3000.app.github.dev",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _initialize_runtime() -> None:
    load_dotenv(DOTENV_PATH)
    conn = connect()
    try:
        init_db(conn)
    finally:
        conn.close()


# Initialize once on import and on app startup to keep table creation idempotent.
_initialize_runtime()


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _market_cache_max_age_seconds() -> int:
    raw = os.getenv("MEI_MARKET_CACHE_MAX_AGE_SECONDS", "3600")
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        return 3600
    return max(0, parsed)


def panel_status(percentile, slope):
    if percentile is None or slope is None:
        return "partial"
    return "ok"


def _compute_outputs(series: list[float], lookback: int, trend_window: int = 60) -> dict:
    percentile = None
    regime = None
    slope = None
    trend_direction = None
    had_error = False
    partial = False

    try:
        percentile = round(rolling_percentile(series, lookback=lookback), 2)
        regime = classify_regime(percentile)
    except ValueError:
        partial = True
        percentile = None
        regime = None
    except Exception:
        had_error = True

    try:
        trend_series = series[-trend_window:] if len(series) > trend_window else series
        slope = round(trend_slope(trend_series), 4)
        trend_direction = "Up" if slope > 0 else "Down" if slope < 0 else "Flat"
    except ValueError:
        partial = True
        slope = None
        trend_direction = None
    except Exception:
        had_error = True

    status = "error" if had_error else "partial" if partial else panel_status(percentile, slope)
    if status == "partial":
        percentile = None
        regime = None
        slope = None
        trend_direction = None

    return {
        "percentile": percentile,
        "regime": regime,
        "slope": slope,
        "trend_direction": trend_direction,
        "status": status,
    }


def build_panel(
    panel_id: str, title: str, series: list[float], lookback: int, tab_name: str
) -> dict:
    timestamp = _iso_now()
    computed = _compute_outputs(series, lookback)

    percentile = computed["percentile"]
    regime = computed["regime"]
    slope = computed["slope"]
    trend_direction = computed["trend_direction"]
    status = computed["status"]

    raw_metrics = [
        {
            "key": "latest_value",
            "value": round(series[-1], 4) if series and status != "partial" else None,
            "unit": "",
        },
        {"key": "percentile_lookback", "value": percentile, "unit": ""},
        {"key": "regime", "value": regime, "unit": ""},
        {"key": "trend_slope", "value": slope, "unit": ""},
        {"key": "trend_direction", "value": trend_direction, "unit": ""},
    ]

    panel = {
        "id": panel_id,
        "title": title,
        "raw_metrics": raw_metrics,
        "context": [],
        "interpretation": [],
        "why_toggle": "",
        "status": status,
        "last_updated": timestamp,
    }

    generated = generate_interpretation(tab_name, panel)
    panel["context"] = generated["context"]
    panel["interpretation"] = generated["interpretation"]
    panel["why_toggle"] = generated["why_toggle"]

    return panel


def _dominant(counts: dict, precedence: list[str]) -> str:
    max_count = max(counts.values()) if counts else 0
    for label in precedence:
        if counts.get(label, 0) == max_count:
            return label
    return precedence[-1]


def _aggregate_tab_signals(panels: list[dict]) -> dict:
    regime_counts = {"High": 0, "Mid": 0, "Low": 0, "Unknown": 0}
    trend_counts = {"Down": 0, "Flat": 0, "Up": 0, "Unknown": 0}
    tension_label_counts = {
        "High+Down": 0,
        "High+Flat": 0,
        "Mid+Down": 0,
        "Low+Up": 0,
        "Trend unavailable": 0,
    }
    tension_panels = 0

    for panel in panels:
        signals = extract_signals(panel)
        regime = signals.get("regime", "Unknown")
        trend = signals.get("trend_direction", "Unknown")

        regime_counts[regime if regime in regime_counts else "Unknown"] += 1
        trend_counts[trend if trend in trend_counts else "Unknown"] += 1

        tensions = detect_tensions(signals)
        if tensions:
            tension_panels += 1
        for tension in tensions:
            label = tension.get("label", "")
            if label in tension_label_counts:
                tension_label_counts[label] += 1

    sorted_tensions = sorted(
        tension_label_counts.items(),
        key=lambda item: (-item[1], TENSION_LABEL_ORDER.index(item[0])),
    )
    top_tensions = [label for label, count in sorted_tensions if count > 0][:2]

    return {
        "regime_counts": regime_counts,
        "trend_counts": trend_counts,
        "tension_panels": tension_panels,
        "top_tensions": top_tensions,
        "dominant_regime": _dominant(regime_counts, ["High", "Mid", "Low", "Unknown"]),
        "dominant_trend": _dominant(trend_counts, ["Down", "Flat", "Up", "Unknown"]),
    }


def build_payload(tab_name: str, panel_specs: list[dict]) -> dict:
    timestamp = _iso_now()
    panels = [
        build_panel(
            panel_id=spec["id"],
            title=spec["title"],
            series=spec["series"],
            lookback=spec["lookback"],
            tab_name=tab_name,
        )
        for spec in panel_specs
    ]
    status_counts = {"ok": 0, "partial": 0, "error": 0}
    for p in panels:
        status_counts[p["status"]] += 1

    panel_count = len(panels)
    aggregates = _aggregate_tab_signals(panels)
    regime_counts = aggregates["regime_counts"]
    trend_counts = aggregates["trend_counts"]
    dominant_regime = aggregates["dominant_regime"]
    dominant_trend = aggregates["dominant_trend"]
    tension_panels = aggregates["tension_panels"]
    top_tensions = aggregates["top_tensions"]
    top_tension_text = ", ".join(top_tensions) if top_tensions else "none"

    conditional_sensitivity = [
        guard_language(
            f"If dominant regime shifts from {dominant_regime} to a lower-intensity bucket, risk-posture wording may need recalibration."
        ),
        guard_language(
            f"If trend direction shifts from {dominant_trend} to an opposing state, current tension classifications may change."
        ),
        guard_language(
            f"If partial panels decrease from {status_counts['partial']}/{panel_count}, interpretation confidence language may become more specific."
        ),
    ]

    summary = [
        guard_language(
            f"Overview: Dominant regime is {dominant_regime} with {dominant_trend} trend across this tab."
        ),
        guard_language(
            f"Regimes: High={regime_counts['High']}, Mid={regime_counts['Mid']}, Low={regime_counts['Low']}, Unknown={regime_counts['Unknown']}."
        ),
        guard_language(
            f"Trends: Down={trend_counts['Down']}, Flat={trend_counts['Flat']}, Up={trend_counts['Up']}, Unknown={trend_counts['Unknown']}."
        ),
        guard_language(
            f"Tensions: {tension_panels} panels show mixed signals (top: {top_tension_text})."
        ),
        guard_language(
            "Notes: Interpretation is descriptive and based on current computed metrics."
        ),
    ]

    return {
        "tab": tab_name,
        "last_updated": timestamp,
        "panels": panels,
        "conditional_sensitivity": conditional_sensitivity,
        "summary": summary,
    }


# Backward-compatible wrapper for existing tests that call _build_panel directly.
def _build_panel(
    panel_id: str, title: str, series: list[float], lookback: int, timestamp: str
) -> dict:
    panel = build_panel(panel_id, title, series, lookback, tab_name="test")
    panel["last_updated"] = timestamp
    return panel


@app.get("/")
def root():
    return {
        "service": "MEI backend",
        "endpoints": [
            "/api/intraday",
            "/api/swing",
            "/api/market/status",
            "/api/snapshots/latest",
            "/api/snapshots/{snapshot_id}",
            "/api/audit",
            "/health",
        ],
    }


@app.get("/health")
def health():
    return {"ok": True}


def _source_status(
    conn,
    cache_key: str,
    provider: str,
    ticker: str,
    max_age_seconds: int,
) -> dict:
    now = datetime.now(timezone.utc)
    entry = get_cache_entry(conn, cache_key)
    if entry is None:
        return {
            "provider": provider,
            "ticker": ticker,
            "cached": False,
            "age_seconds": None,
            "fetched_at": None,
            "rows": 0,
        }

    fetched_dt = entry.get("fetched_dt")
    age_seconds = None
    if isinstance(fetched_dt, datetime):
        age_seconds = max(0, int((now - fetched_dt).total_seconds()))

    cached = age_seconds is not None and age_seconds <= max_age_seconds

    return {
        "provider": provider,
        "ticker": ticker,
        "cached": cached,
        "age_seconds": age_seconds,
        "fetched_at": entry.get("fetched_at"),
        "rows": entry.get("rows", 0),
    }


@app.get("/api/market/status")
def get_market_status():
    max_age_seconds = _market_cache_max_age_seconds()
    spy_ticker = os.getenv("MEI_SPY_TICKER", "SPY")
    vix_ticker = os.getenv("MEI_VIX_TICKER", "I:VIX")
    yield_series = os.getenv("MEI_YIELD_SERIES", "DGS10")

    conn = connect()
    try:
        init_db(conn)
        sources = {
            "spy": _source_status(
                conn,
                cache_key=spy_cache_key(),
                provider="polygon",
                ticker=spy_ticker,
                max_age_seconds=max_age_seconds,
            ),
            "vix": _source_status(
                conn,
                cache_key=vix_cache_key(),
                provider="polygon",
                ticker=vix_ticker,
                max_age_seconds=max_age_seconds,
            ),
            "yield": _source_status(
                conn,
                cache_key=yield_cache_key(),
                provider="fred",
                ticker=yield_series,
                max_age_seconds=max_age_seconds,
            ),
        }
    finally:
        conn.close()

    return {"sources": sources}


def _extract_numeric_series(rows: list[dict], value_key: str) -> list[float]:
    series: list[float] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = row.get(value_key)
        if isinstance(value, (int, float)):
            series.append(float(value))
    return series


def _build_intraday_panel_specs(conn) -> list[dict]:
    spy_rows = get_spy_daily(conn)
    vix_rows = get_vix_daily(conn)
    yield_rows = get_yield_daily(conn)

    spy_close = _extract_numeric_series(spy_rows, "close")
    vix_close = _extract_numeric_series(vix_rows, "close")
    yield_value = [value for value in _extract_numeric_series(yield_rows, "value") if value > 0]

    return [
        {
            "id": "intraday_spy_state",
            "title": "Intraday SPY State",
            "series": spy_close,
            "lookback": 20,
        },
        {
            "id": "intraday_vix_state",
            "title": "Intraday VIX State",
            "series": vix_close,
            "lookback": 20,
        },
        {
            "id": "intraday_yield_state",
            "title": "Intraday 10Y Yield State",
            "series": yield_value,
            "lookback": 20,
        },
    ]


@app.get("/api/intraday")
def get_intraday():
    return _build_with_persistence(tab="intraday", panel_specs_builder=_build_intraday_panel_specs)


@app.get("/api/swing")
def get_swing():
    panel_specs = [
        {
            "id": "swing_vol_state",
            "title": "Swing Volatility State",
            "series": [
                1.30,
                1.29,
                1.28,
                1.27,
                1.26,
                1.25,
                1.24,
                1.23,
                1.22,
                1.21,
                1.20,
                1.19,
                1.18,
                1.17,
                1.16,
                1.15,
                1.14,
                1.13,
                1.12,
                1.11,
                1.10,
            ],
            "lookback": 20,
        }
    ]
    return _build_with_persistence(tab="swing", panel_specs=panel_specs)


def _build_with_persistence(
    tab: str,
    panel_specs: list[dict] | None = None,
    panel_specs_builder=None,
) -> dict:
    forced_fail_tab = os.getenv("MEI_FORCE_FAIL_TAB", "").strip().lower()
    try:
        if forced_fail_tab == tab:
            raise RuntimeError("forced failure")

        conn = connect()
        try:
            init_db(conn)
            specs = panel_specs if panel_specs is not None else []
            if panel_specs_builder is not None:
                specs = panel_specs_builder(conn)

            payload = build_payload(tab, specs)
            save_snapshot(conn, tab=tab, payload=payload)
        finally:
            conn.close()

        return payload
    except Exception as exc:
        conn = connect()
        try:
            init_db(conn)
            log_action(conn, tab=tab, action="build_failed", detail=str(exc))
            last_good = get_last_good_snapshot(conn, tab=tab)
            if last_good is not None:
                log_action(
                    conn,
                    tab=tab,
                    action="served_last_good",
                    detail=f"{tab} build failed; served last good snapshot",
                )
                return last_good
        finally:
            conn.close()

        raise


def _normalize_tab(tab: str) -> str:
    normalized = str(tab).strip().lower()
    if normalized not in {"intraday", "swing"}:
        raise ValueError("tab must be 'intraday' or 'swing'")
    return normalized


def _clamp_limit(value: int, default: int, minimum: int, maximum: int) -> int:
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        numeric = default
    return max(minimum, min(numeric, maximum))


@app.get("/api/snapshots/latest")
def get_snapshots_latest(tab: str, limit: int = 10):
    try:
        normalized_tab = _normalize_tab(tab)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

    bounded_limit = _clamp_limit(limit, default=10, minimum=1, maximum=50)

    conn = connect()
    try:
        init_db(conn)
        snapshots = list_snapshots(conn, tab=normalized_tab, limit=bounded_limit)
    finally:
        conn.close()

    return {
        "tab": normalized_tab,
        "count": len(snapshots),
        "snapshots": snapshots,
    }


@app.get("/api/snapshots/{snapshot_id}")
def get_snapshot(snapshot_id: int):
    conn = connect()
    try:
        init_db(conn)
        snapshot = get_snapshot_by_id(conn, snapshot_id=snapshot_id)
    finally:
        conn.close()

    if snapshot is None:
        return JSONResponse({"error": "not found"}, status_code=404)

    return snapshot


@app.get("/api/audit")
def get_audit(tab: str | None = None, limit: int = 50):
    normalized_tab = None
    if tab is not None:
        try:
            normalized_tab = _normalize_tab(tab)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    bounded_limit = _clamp_limit(limit, default=50, minimum=1, maximum=200)

    conn = connect()
    try:
        init_db(conn)
        events = list_audit(conn, tab=normalized_tab, limit=bounded_limit)
    finally:
        conn.close()

    return {"count": len(events), "events": events}
