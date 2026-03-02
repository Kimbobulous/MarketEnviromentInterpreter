from datetime import datetime, timezone
from contextlib import asynccontextmanager
import math
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
    get_daily_ohlc,
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


def _build_payload_from_panels(tab_name: str, panels: list[dict]) -> dict:
    timestamp = _iso_now()
    status_counts = {"ok": 0, "partial": 0, "error": 0}
    for p in panels:
        panel_status_value = p.get("status", "")
        if panel_status_value in status_counts:
            status_counts[panel_status_value] += 1

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
    if tab_name == "swing":
        summary.append(
            guard_language(
                "Coverage: Swing proxies cover breadth (RSP/SPY), concentration (QQQ/SPY), credit risk appetite (HYG/SHY), and volatility conditions."
            )
        )

    return {
        "tab": tab_name,
        "last_updated": timestamp,
        "panels": panels,
        "conditional_sensitivity": conditional_sensitivity,
        "summary": summary,
    }


def build_payload(tab_name: str, panel_specs: list[dict]) -> dict:
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
    return _build_payload_from_panels(tab_name, panels)


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


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name, str(default))
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        return default
    return max(minimum, parsed)


def _rows_to_close_map(rows: list[dict]) -> dict[str, float]:
    out: dict[str, float] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_date = row.get("date")
        close = row.get("close")
        if isinstance(row_date, str) and isinstance(close, (int, float)) and close > 0:
            out[row_date] = float(close)
    return out


def _build_log_ratio_series(rows_a: list[dict], rows_b: list[dict]) -> list[float]:
    a_by_date = _rows_to_close_map(rows_a)
    b_by_date = _rows_to_close_map(rows_b)
    common_dates = sorted(set(a_by_date.keys()) & set(b_by_date.keys()))
    series: list[float] = []
    for row_date in common_dates:
        a_close = a_by_date.get(row_date)
        b_close = b_by_date.get(row_date)
        if not isinstance(a_close, float) or not isinstance(b_close, float):
            continue
        if a_close <= 0 or b_close <= 0:
            continue
        series.append(math.log(a_close / b_close))
    return series


def _safe_daily_rows(conn, ticker: str) -> tuple[list[dict], str | None]:
    try:
        return get_daily_ohlc(conn, symbol=ticker), None
    except RuntimeError:
        return [], f"{ticker} series unavailable."


def _build_swing_proxy_panel(
    panel_id: str,
    title: str,
    source_tickers: str,
    series: list[float],
    trend_lookback: int,
    pctl_lookback: int,
    data_note: str | None = None,
) -> dict:
    timestamp = _iso_now()
    status = "ok"
    latest = None
    percentile = None
    regime = None
    slope = None
    trend_direction = None
    had_error = False

    if not series:
        status = "partial"
    else:
        try:
            latest = round(series[-1], 6)
            percentile = round(rolling_percentile(series, lookback=pctl_lookback), 2)
            regime = classify_regime(percentile)
        except ValueError:
            status = "partial"
        except Exception:
            had_error = True

        try:
            trend_window = series[-trend_lookback:] if len(series) > trend_lookback else series
            trend_input = [math.exp(value) for value in trend_window]
            slope = round(trend_slope(trend_input), 4)
            trend_direction = "Up" if slope > 0 else "Down" if slope < 0 else "Flat"
        except ValueError:
            status = "partial"
        except Exception:
            had_error = True

    if had_error:
        status = "error"

    if status == "partial":
        latest = None
        percentile = None
        regime = None
        slope = None
        trend_direction = None

    raw_metrics = [
        {"key": "latest", "value": latest, "unit": ""},
        {"key": "percentile_lookback", "value": percentile, "unit": ""},
        {"key": "regime", "value": regime, "unit": ""},
        {"key": "trend_slope", "value": slope, "unit": ""},
        {"key": "trend_direction", "value": trend_direction, "unit": ""},
        {"key": "source_tickers", "value": source_tickers, "unit": ""},
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

    generated = generate_interpretation("swing", panel)
    panel["context"] = generated["context"]
    panel["interpretation"] = generated["interpretation"]
    panel["why_toggle"] = generated["why_toggle"]

    if status == "partial" and isinstance(data_note, str) and data_note:
        panel["interpretation"].append(guard_language(f"Data note: {data_note}"))

    return panel


def _build_swing_panels(conn) -> list[dict]:
    breadth_a = os.getenv("MEI_SWING_BREADTH_A", "RSP")
    breadth_b = os.getenv("MEI_SWING_BREADTH_B", "SPY")
    conc_a = os.getenv("MEI_SWING_CONC_A", "QQQ")
    conc_b = os.getenv("MEI_SWING_CONC_B", "SPY")
    sent_a = os.getenv("MEI_SWING_SENT_A", "HYG")
    sent_b = os.getenv("MEI_SWING_SENT_B", "SHY")
    swing_vix = os.getenv("MEI_SWING_VIX_TICKER", "I:VIX")
    swing_vol_etf = os.getenv("MEI_SWING_VOL_ETF", "VXX")
    trend_lookback = _env_int("MEI_SWING_LOOKBACK", default=60, minimum=2)
    pctl_lookback = _env_int("MEI_SWING_PCTL_LOOKBACK", default=20, minimum=2)

    breadth_a_rows, breadth_a_note = _safe_daily_rows(conn, breadth_a)
    breadth_b_rows, breadth_b_note = _safe_daily_rows(conn, breadth_b)
    conc_a_rows, conc_a_note = _safe_daily_rows(conn, conc_a)
    conc_b_rows, conc_b_note = _safe_daily_rows(conn, conc_b)
    sent_a_rows, sent_a_note = _safe_daily_rows(conn, sent_a)
    sent_b_rows, sent_b_note = _safe_daily_rows(conn, sent_b)
    vix_rows, vix_note = _safe_daily_rows(conn, swing_vix)
    vol_rows, vol_note = _safe_daily_rows(conn, swing_vol_etf)

    breadth_note = " ".join([note for note in [breadth_a_note, breadth_b_note] if note]) or None
    conc_note = " ".join([note for note in [conc_a_note, conc_b_note] if note]) or None
    sent_note = " ".join([note for note in [sent_a_note, sent_b_note] if note]) or None
    vol_combined_note = " ".join([note for note in [vix_note, vol_note] if note]) or None

    panels = [
        _build_swing_proxy_panel(
            panel_id="swing_breadth_participation",
            title="Swing Breadth Participation",
            source_tickers=f"{breadth_a}/{breadth_b}",
            series=_build_log_ratio_series(breadth_a_rows, breadth_b_rows),
            trend_lookback=trend_lookback,
            pctl_lookback=pctl_lookback,
            data_note=breadth_note,
        ),
        _build_swing_proxy_panel(
            panel_id="swing_concentration_tilt",
            title="Swing Concentration Tilt",
            source_tickers=f"{conc_a}/{conc_b}",
            series=_build_log_ratio_series(conc_a_rows, conc_b_rows),
            trend_lookback=trend_lookback,
            pctl_lookback=pctl_lookback,
            data_note=conc_note,
        ),
        _build_swing_proxy_panel(
            panel_id="swing_risk_sentiment",
            title="Swing Risk Sentiment",
            source_tickers=f"{sent_a}/{sent_b}",
            series=_build_log_ratio_series(sent_a_rows, sent_b_rows),
            trend_lookback=trend_lookback,
            pctl_lookback=pctl_lookback,
            data_note=sent_note,
        ),
        _build_swing_proxy_panel(
            panel_id="swing_vol_term_structure",
            title="Swing Volatility Term Structure Proxy",
            source_tickers=f"{swing_vol_etf}/{swing_vix}",
            series=_build_log_ratio_series(vol_rows, vix_rows),
            trend_lookback=trend_lookback,
            pctl_lookback=pctl_lookback,
            data_note=vol_combined_note,
        ),
    ]
    return panels


def _build_swing_payload(conn) -> dict:
    panels = _build_swing_panels(conn)
    return _build_payload_from_panels("swing", panels)


@app.get("/api/intraday")
def get_intraday():
    return _build_with_persistence(tab="intraday", panel_specs_builder=_build_intraday_panel_specs)


@app.get("/api/swing")
def get_swing():
    return _build_with_persistence(tab="swing", payload_builder=_build_swing_payload)


def _build_with_persistence(
    tab: str,
    panel_specs: list[dict] | None = None,
    panel_specs_builder=None,
    payload_builder=None,
) -> dict:
    forced_fail_tab = os.getenv("MEI_FORCE_FAIL_TAB", "").strip().lower()
    try:
        if forced_fail_tab == tab:
            raise RuntimeError("forced failure")

        conn = connect()
        try:
            init_db(conn)
            if payload_builder is not None:
                payload = payload_builder(conn)
            else:
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
