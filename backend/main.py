from datetime import date, datetime, timedelta, timezone
from contextlib import asynccontextmanager
import json
import logging
import math
import os

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

try:
    from lib.compute import (
        classify_regime,
        rolling_percentile,
        rolling_percentile_series,
        trend_slope,
    )
    from lib.db import connect, init_db
    from lib.env import load_dotenv
    from lib.interpret import (
        detect_tensions,
        extract_signals,
        generate_interpretation,
        guard_language,
    )
    from lib.market_data.cache import get_cache_entry
    from lib.market_data.client import (
        daily_ohlc_cache_key,
        get_daily_ohlc,
        get_spy_daily,
        get_vix_daily,
        get_yield_daily,
        spy_cache_key,
        yield_cache_key,
    )
    from lib.snapshots import get_snapshot_by_id, list_audit, list_snapshots
    from lib.snapshots import get_last_good_snapshot, log_action, save_snapshot
    from lib.weighting import build_structured_summary, classify_summary, score_forces
except ModuleNotFoundError:  # package-context fallback for tests/importers
    from .lib.compute import (
        classify_regime,
        rolling_percentile,
        rolling_percentile_series,
        trend_slope,
    )
    from .lib.db import connect, init_db
    from .lib.env import load_dotenv
    from .lib.interpret import (
        detect_tensions,
        extract_signals,
        generate_interpretation,
        guard_language,
    )
    from .lib.market_data.cache import get_cache_entry
    from .lib.market_data.client import (
        daily_ohlc_cache_key,
        get_daily_ohlc,
        get_spy_daily,
        get_vix_daily,
        get_yield_daily,
        spy_cache_key,
        yield_cache_key,
    )
    from .lib.snapshots import get_snapshot_by_id, list_audit, list_snapshots
    from .lib.snapshots import get_last_good_snapshot, log_action, save_snapshot
    from .lib.weighting import build_structured_summary, classify_summary, score_forces

BACKEND_DIR = os.path.dirname(__file__)
DOTENV_PATH = os.path.join(BACKEND_DIR, ".env")
DEFAULT_INTRADAY_PCTL_LOOKBACK = 126
DEFAULT_SWING_PCTL_LOOKBACK = 252
DEFAULT_TREND_LOOKBACK = 126
DEFAULT_SERIES_TARGET_BARS = 252
DEFAULT_SERIES_MIN_BARS = 120
ALLOWED_LOOKBACKS = {20, 60, 252}
DEFAULT_PCTL_SANITY_SAMPLE_WINDOW = 120
SOURCE_LAST_ERRORS = {"spy": None, "vix": None, "yield": None}
logger = logging.getLogger("mei.market")


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


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name, str(default))
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        return default
    return max(minimum, parsed)


def _quant_config() -> dict[str, int]:
    intraday_pctl_lookback = _env_int(
        "MEI_INTRADAY_PCTL_LOOKBACK",
        default=DEFAULT_INTRADAY_PCTL_LOOKBACK,
        minimum=2,
    )
    swing_pctl_lookback = _env_int(
        "MEI_SWING_PCTL_LOOKBACK",
        default=DEFAULT_SWING_PCTL_LOOKBACK,
        minimum=2,
    )
    legacy_swing_lookback = _env_int(
        "MEI_SWING_LOOKBACK",
        default=DEFAULT_TREND_LOOKBACK,
        minimum=2,
    )
    trend_lookback = _env_int(
        "MEI_TREND_LOOKBACK",
        default=legacy_swing_lookback,
        minimum=2,
    )
    series_min = _env_int("MEI_SERIES_MIN_BARS", default=DEFAULT_SERIES_MIN_BARS, minimum=1)
    series_target = _env_int(
        "MEI_SERIES_TARGET_BARS",
        default=DEFAULT_SERIES_TARGET_BARS,
        minimum=series_min,
    )

    return {
        "intraday_pctl_lookback": intraday_pctl_lookback,
        "swing_pctl_lookback": swing_pctl_lookback,
        "trend_lookback": trend_lookback,
        "series_target_bars": series_target,
        "series_min_bars": series_min,
    }


def _resolve_selected_lookback(lookback: int | None) -> int | None:
    if lookback is None:
        return None
    if lookback in ALLOWED_LOOKBACKS:
        return lookback
    raise HTTPException(
        status_code=400,
        detail="Invalid lookback. Allowed values are: 20, 60, 252.",
    )


def _set_source_last_error(source_key: str, error: Exception | str | None) -> None:
    if not isinstance(source_key, str) or source_key not in SOURCE_LAST_ERRORS:
        return
    if error is None:
        SOURCE_LAST_ERRORS[source_key] = None
        return
    SOURCE_LAST_ERRORS[source_key] = str(error)


def _vix_ticker_candidates() -> list[str]:
    primary = os.getenv("MEI_VIX_TICKER", "I:VIX").strip() or "I:VIX"
    proxy = os.getenv("MEI_VIX_PROXY_TICKER", "").strip()
    if not proxy:
        proxy = os.getenv("MEI_SWING_VOL_ETF", "VXX").strip() or "VXX"

    out: list[str] = []
    for ticker in [primary, proxy]:
        if ticker and ticker not in out:
            out.append(ticker)
    return out


def _is_proxy_vix_ticker(ticker: str) -> bool:
    return not str(ticker).upper().startswith("I:")


def _is_forbidden_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "forbidden" in text or "403" in text


def _select_vix_status_symbol(conn) -> str:
    candidates = _vix_ticker_candidates()
    chosen = candidates[0] if candidates else "I:VIX"
    chosen_rows = -1
    chosen_fetched = ""
    for ticker in candidates:
        key = daily_ohlc_cache_key(symbol=ticker)
        entry = get_cache_entry(conn, key)
        if entry is None:
            continue
        rows = int(entry.get("rows", 0) or 0)
        fetched_at = str(entry.get("fetched_at", "") or "")
        if rows > chosen_rows:
            chosen = ticker
            chosen_rows = rows
            chosen_fetched = fetched_at
            continue
        if rows == chosen_rows and fetched_at > chosen_fetched:
            chosen = ticker
            chosen_fetched = fetched_at
    return chosen


def _fetch_intraday_vix_rows(conn) -> tuple[list[dict], str]:
    candidates = _vix_ticker_candidates()
    if not candidates:
        raise RuntimeError("No VIX ticker candidates configured")

    primary = candidates[0]
    try:
        rows = get_vix_daily(conn)
        _set_source_last_error("vix", None)
        return rows, primary
    except Exception as exc:
        _set_source_last_error("vix", exc)
        if len(candidates) < 2 or not _is_forbidden_error(exc):
            raise

        proxy = candidates[1]
        logger.warning(
            "Primary VIX source '%s' unavailable; using proxy '%s'.",
            primary,
            proxy,
        )
        rows = get_daily_ohlc(conn, symbol=proxy)
        _set_source_last_error("vix", None)
        return rows, proxy


def panel_status(percentile, slope):
    if percentile is None or slope is None:
        return "partial"
    return "ok"


def _is_iso_date_string(value) -> bool:
    if not isinstance(value, str):
        return False
    if len(value) != 10:
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _fallback_business_day_times(count: int) -> list[str]:
    if count <= 0:
        return []

    out: list[str] = []
    cursor = date(2000, 1, 3)  # Monday
    while len(out) < count:
        if cursor.weekday() < 5:
            out.append(cursor.isoformat())
        cursor += timedelta(days=1)
    return out


def _compute_outputs(
    series: list[float],
    lookback: int,
    trend_window: int,
    series_min: int,
) -> dict:
    percentile = None
    regime = None
    slope = None
    trend_direction = None
    had_error = False
    partial = False

    min_required_points = max(series_min, lookback + 1, trend_window)
    if len(series) < min_required_points:
        partial = True

    if partial:
        return {
            "percentile": None,
            "regime": None,
            "slope": None,
            "trend_direction": None,
            "status": "partial",
        }

    try:
        percentile_raw = rolling_percentile(series, lookback=lookback)
        if percentile_raw is None:
            partial = True
            percentile = None
            regime = None
        else:
            percentile = round(percentile_raw, 2)
            regime = classify_regime(percentile)
    except ValueError:
        partial = True
        percentile = None
        regime = None
    except Exception:
        had_error = True

    try:
        trend_series = series[-trend_window:]
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


def _panel_sparkline_with_times(
    series: list[float], series_dates: list[str] | None = None, max_points: int = 60
) -> tuple[list[float], list[str]]:
    """Return capped sparkline values and aligned ISO date labels."""
    if not isinstance(series, list):
        return [], []

    if isinstance(series_dates, list) and len(series_dates) == len(series):
        paired: list[tuple[float, str]] = []
        for value, row_date in zip(series, series_dates):
            if not isinstance(value, (int, float)):
                continue
            if not _is_iso_date_string(row_date):
                continue
            paired.append((float(value), row_date))

        tail_pairs = paired[-max_points:] if len(paired) > max_points else paired
        sparkline = [value for value, _row_date in tail_pairs]
        sparkline_times = [row_date for _value, row_date in tail_pairs]
        return sparkline, sparkline_times

    numeric_values = [float(value) for value in series if isinstance(value, (int, float))]
    sparkline = numeric_values[-max_points:] if len(numeric_values) > max_points else numeric_values
    sparkline_times = _fallback_business_day_times(len(sparkline))
    return sparkline, sparkline_times


def build_panel(
    panel_id: str,
    title: str,
    series: list[float],
    lookback: int,
    tab_name: str,
    series_dates: list[str] | None = None,
    trend_lookback: int | None = None,
    series_target: int | None = None,
    series_min: int | None = None,
    lookback_selected: int | None = None,
) -> dict:
    timestamp = _iso_now()
    quant = _quant_config()
    resolved_trend_lookback = trend_lookback or quant["trend_lookback"]
    resolved_series_min = series_min or quant["series_min_bars"]
    resolved_series_target = series_target or quant["series_target_bars"]
    computed = _compute_outputs(
        series,
        lookback=lookback,
        trend_window=resolved_trend_lookback,
        series_min=resolved_series_min,
    )

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

    sparkline, sparkline_times = _panel_sparkline_with_times(series, series_dates)

    panel = {
        "id": panel_id,
        "title": title,
        "raw_metrics": raw_metrics,
        "sparkline": sparkline,
        "sparkline_times": sparkline_times,
        "context": [],
        "interpretation": [],
        "why_toggle": "",
        "status": status,
        "last_updated": timestamp,
        "window_meta": {
            "series_points": len(series),
            "series_target": resolved_series_target,
            "series_min": resolved_series_min,
            "pctl_lookback": lookback,
            "trend_lookback": resolved_trend_lookback,
            "pctl_excludes_current": True,
        },
    }
    if lookback_selected is not None:
        panel["window_meta"]["lookback_selected"] = lookback_selected

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


def _build_payload_from_panels(
    tab_name: str,
    panels: list[dict],
    lookback_selected: int | None = None,
) -> dict:
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
    tension_panels = aggregates["tension_panels"]
    force_scores = score_forces(tab_name, panels)
    force_summary = classify_summary(force_scores, tension_panels=tension_panels)
    sorted_forces = force_summary.get("sorted_forces", [])
    dominant_force = force_summary.get("dominant_force", "unknown")
    second_force = (
        sorted_forces[1][0]
        if isinstance(sorted_forces, list)
        and len(sorted_forces) > 1
        and isinstance(sorted_forces[1], tuple)
        else "supporting_forces"
    )

    conditional_sensitivity = [
        guard_language(
            f"If {dominant_force} signals soften (e.g., regime shifts lower), leadership may rotate."
        ),
        guard_language(
            f"If {second_force} strengthens, mixed leadership could increase."
        ),
    ]
    if status_counts["partial"] > 0:
        conditional_sensitivity.append(
            guard_language(
                f"If partial panels decline from {status_counts['partial']}/{panel_count}, confidence language may become more specific."
            )
        )
    if tension_panels > 0 and len(conditional_sensitivity) < 4:
        conditional_sensitivity.append(
            guard_language(
                f"If tension count changes from {tension_panels}, force leadership balance may shift."
            )
        )

    summary = build_structured_summary(tab_name, force_summary)
    summary.append(
        guard_language(
            "Diagnostics: Regimes H="
            f"{regime_counts['High']} M={regime_counts['Mid']} L={regime_counts['Low']}; "
            "Trends U="
            f"{trend_counts['Up']} F={trend_counts['Flat']} D={trend_counts['Down']}; "
            f"Tensions={tension_panels}."
        )
    )

    payload = {
        "tab": tab_name,
        "last_updated": timestamp,
        "panels": panels,
        "conditional_sensitivity": conditional_sensitivity,
        "summary": summary,
    }
    if lookback_selected is not None:
        payload["window_meta"] = {"lookback_selected": lookback_selected}
    return payload


def build_payload(
    tab_name: str,
    panel_specs: list[dict],
    lookback_selected: int | None = None,
) -> dict:
    panels = [
        build_panel(
            panel_id=spec["id"],
            title=spec["title"],
            series=spec["series"],
            lookback=spec["lookback"],
            tab_name=tab_name,
            series_dates=spec.get("series_dates"),
            trend_lookback=spec.get("trend_lookback"),
            series_target=spec.get("series_target"),
            series_min=spec.get("series_min"),
            lookback_selected=lookback_selected,
        )
        for spec in panel_specs
    ]
    return _build_payload_from_panels(tab_name, panels, lookback_selected=lookback_selected)


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
            "/api/debug/percentile_sanity",
            "/api/snapshots/latest",
            "/api/snapshots/{snapshot_id}",
            "/api/audit",
            "/health",
        ],
    }


@app.get("/health")
def health():
    return {"ok": True}


def _debug_sanity_sample_window() -> int:
    return _env_int(
        "MEI_DEBUG_PCTL_SANITY_WINDOW",
        default=DEFAULT_PCTL_SANITY_SAMPLE_WINDOW,
        minimum=1,
    )


def _round_or_none(value: float | None, ndigits: int = 4) -> float | None:
    if not isinstance(value, (int, float)):
        return None
    return round(float(value), ndigits)


def _exact_count(values: list[float], target: float) -> int:
    return sum(1 for value in values if math.isclose(value, target, abs_tol=1e-12))


def _percentile_summary(
    series: list[float],
    lookback: int,
    sample_window: int,
) -> dict:
    percentiles = rolling_percentile_series(series, lookback=lookback)
    tail = percentiles[-sample_window:] if len(percentiles) > sample_window else percentiles

    if not tail:
        return {
            "lookback": lookback,
            "sample_size_available": len(series),
            "computed_percentiles": len(percentiles),
            "sample_size_window": 0,
            "sample_window": sample_window,
            "min": None,
            "max": None,
            "mean": None,
            "count_le_5": 0,
            "count_ge_95": 0,
            "count_eq_0": 0,
            "count_eq_100": 0,
        }

    return {
        "lookback": lookback,
        "sample_size_available": len(series),
        "computed_percentiles": len(percentiles),
        "sample_size_window": len(tail),
        "sample_window": sample_window,
        "min": _round_or_none(min(tail)),
        "max": _round_or_none(max(tail)),
        "mean": _round_or_none(sum(tail) / float(len(tail))),
        "count_le_5": sum(1 for value in tail if value <= 5.0),
        "count_ge_95": sum(1 for value in tail if value >= 95.0),
        "count_eq_0": _exact_count(tail, 0.0),
        "count_eq_100": _exact_count(tail, 100.0),
    }


def _series_values_for_sanity(
    conn,
    loader,
    value_key: str,
    positive_only: bool = False,
) -> tuple[list[float], str | None]:
    try:
        rows = loader(conn)
        values, dates = _extract_numeric_series_with_dates(rows, value_key)
        if positive_only:
            filtered = [
                value
                for value, row_date in zip(values, dates)
                if value > 0 and _is_iso_date_string(row_date)
            ]
            return filtered, None
        return values, None
    except Exception as exc:
        return [], str(exc)


@app.get("/api/debug/percentile_sanity")
def get_percentile_sanity():
    lookbacks = [126, 252]
    sample_window = _debug_sanity_sample_window()
    vxx_ticker = (
        os.getenv("MEI_VIX_PROXY_TICKER", "").strip()
        or os.getenv("MEI_SWING_VOL_ETF", "VXX").strip()
        or "VXX"
    )
    dgs10_series = os.getenv("MEI_YIELD_SERIES", "DGS10")

    conn = connect()
    try:
        init_db(conn)
        spy_values, spy_error = _series_values_for_sanity(
            conn, loader=lambda c: get_spy_daily(c), value_key="close"
        )
        vxx_values, vxx_error = _series_values_for_sanity(
            conn,
            loader=lambda c: get_daily_ohlc(c, symbol=vxx_ticker),
            value_key="close",
        )
        dgs10_values, dgs10_error = _series_values_for_sanity(
            conn,
            loader=lambda c: get_yield_daily(c),
            value_key="value",
            positive_only=True,
        )
    finally:
        conn.close()

    return {
        "percentile_excludes_current": True,
        "lookbacks": lookbacks,
        "sample_window": sample_window,
        "series": {
            "spy": {
                "ticker": os.getenv("MEI_SPY_TICKER", "SPY"),
                "sample_size_available": len(spy_values),
                "last_error": spy_error,
                "lookback_summaries": {
                    str(lookback): _percentile_summary(spy_values, lookback, sample_window)
                    for lookback in lookbacks
                },
            },
            "vxx": {
                "ticker": vxx_ticker,
                "sample_size_available": len(vxx_values),
                "last_error": vxx_error,
                "lookback_summaries": {
                    str(lookback): _percentile_summary(vxx_values, lookback, sample_window)
                    for lookback in lookbacks
                },
            },
            "dgs10": {
                "ticker": dgs10_series,
                "sample_size_available": len(dgs10_values),
                "last_error": dgs10_error,
                "lookback_summaries": {
                    str(lookback): _percentile_summary(
                        dgs10_values, lookback, sample_window
                    )
                    for lookback in lookbacks
                },
            },
        },
    }


def _source_status(
    conn,
    source_key: str,
    cache_key: str,
    provider: str,
    ticker: str,
    label: str | None,
    max_age_seconds: int,
    value_key: str,
    positive_only: bool,
    percentile_lookback: int,
    series_min: int,
    series_target: int,
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
            "provider_rows": 0,
            "clean_rows": 0,
            "rows_after_intersection": None,
            "rows_used_for_percentile": None,
            "min_required": series_min,
            "target_required": series_target,
            "last_error": SOURCE_LAST_ERRORS.get(source_key),
            "label": label,
        }

    fetched_dt = entry.get("fetched_dt")
    age_seconds = None
    if isinstance(fetched_dt, datetime):
        age_seconds = max(0, int((now - fetched_dt).total_seconds()))

    cached = age_seconds is not None and age_seconds <= max_age_seconds
    cached_rows = _cache_rows(conn, cache_key)
    provider_rows, clean_rows = _series_row_counts(
        rows=cached_rows,
        value_key=value_key,
        positive_only=positive_only,
    )

    return {
        "provider": provider,
        "ticker": ticker,
        "cached": cached,
        "age_seconds": age_seconds,
        "fetched_at": entry.get("fetched_at"),
        "rows": entry.get("rows", 0),
        "provider_rows": provider_rows,
        "clean_rows": clean_rows,
        "rows_after_intersection": None,
        "rows_used_for_percentile": _rows_used_for_percentile(
            clean_rows=clean_rows,
            lookback=percentile_lookback,
        ),
        "min_required": series_min,
        "target_required": series_target,
        "last_error": SOURCE_LAST_ERRORS.get(source_key),
        "label": label,
    }


def _cache_rows(conn, cache_key: str) -> list[dict]:
    row = conn.execute(
        """
        SELECT data_json
        FROM market_cache
        WHERE cache_key = ?
        LIMIT 1
        """,
        (cache_key,),
    ).fetchone()
    if row is None:
        return []

    payload = row["data_json"]
    if not isinstance(payload, str) or not payload:
        return []

    try:
        parsed = json.loads(payload)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []

    return [item for item in parsed if isinstance(item, dict)]


def _series_row_counts(rows: list[dict], value_key: str, positive_only: bool) -> tuple[int, int]:
    provider_rows = len(rows)
    clean_rows = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_date = row.get("date")
        value = row.get(value_key)
        if not _is_iso_date_string(row_date):
            continue
        if not isinstance(value, (int, float)):
            continue
        if positive_only and value <= 0:
            continue
        clean_rows += 1
    return provider_rows, clean_rows


def _rows_used_for_percentile(clean_rows: int, lookback: int) -> int | None:
    if clean_rows <= 0:
        return None
    return min(max(clean_rows - 1, 0), lookback)


@app.get("/api/market/status")
def get_market_status():
    max_age_seconds = _market_cache_max_age_seconds()
    spy_ticker = os.getenv("MEI_SPY_TICKER", "SPY")
    yield_series = os.getenv("MEI_YIELD_SERIES", "DGS10")
    quant = _quant_config()

    conn = connect()
    try:
        init_db(conn)
        vix_ticker = _select_vix_status_symbol(conn)
        vix_label = (
            f"VIX proxy ({vix_ticker})"
            if _is_proxy_vix_ticker(vix_ticker)
            else "VIX index"
        )
        sources = {
            "spy": _source_status(
                conn,
                source_key="spy",
                cache_key=spy_cache_key(),
                provider="polygon",
                ticker=spy_ticker,
                label="SPY",
                max_age_seconds=max_age_seconds,
                value_key="close",
                positive_only=False,
                percentile_lookback=quant["intraday_pctl_lookback"],
                series_min=quant["series_min_bars"],
                series_target=quant["series_target_bars"],
            ),
            "vix": _source_status(
                conn,
                source_key="vix",
                cache_key=daily_ohlc_cache_key(symbol=vix_ticker),
                provider="polygon",
                ticker=vix_ticker,
                label=vix_label,
                max_age_seconds=max_age_seconds,
                value_key="close",
                positive_only=False,
                percentile_lookback=quant["intraday_pctl_lookback"],
                series_min=quant["series_min_bars"],
                series_target=quant["series_target_bars"],
            ),
            "yield": _source_status(
                conn,
                source_key="yield",
                cache_key=yield_cache_key(),
                provider="fred",
                ticker=yield_series,
                label="10Y yield (FRED)",
                max_age_seconds=max_age_seconds,
                value_key="value",
                positive_only=True,
                percentile_lookback=quant["intraday_pctl_lookback"],
                series_min=quant["series_min_bars"],
                series_target=quant["series_target_bars"],
            ),
        }
    finally:
        conn.close()

    return {"sources": sources}


def _extract_numeric_series_with_dates(
    rows: list[dict], value_key: str
) -> tuple[list[float], list[str]]:
    series: list[float] = []
    dates: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = row.get(value_key)
        row_date = row.get("date")
        if not isinstance(value, (int, float)):
            continue
        if not _is_iso_date_string(row_date):
            continue
        series.append(float(value))
        dates.append(row_date)
    return series, dates


def _build_intraday_panel_specs(conn, lookback_selected: int | None = None) -> list[dict]:
    try:
        spy_rows = get_spy_daily(conn)
        _set_source_last_error("spy", None)
    except Exception as exc:
        _set_source_last_error("spy", exc)
        raise

    vix_rows, used_vix_ticker = _fetch_intraday_vix_rows(conn)

    try:
        yield_rows = get_yield_daily(conn)
        _set_source_last_error("yield", None)
    except Exception as exc:
        _set_source_last_error("yield", exc)
        raise

    spy_close, spy_dates = _extract_numeric_series_with_dates(spy_rows, "close")
    vix_close, vix_dates = _extract_numeric_series_with_dates(vix_rows, "close")
    yield_values, yield_dates_all = _extract_numeric_series_with_dates(yield_rows, "value")
    yield_pairs = [
        (value, row_date)
        for value, row_date in zip(yield_values, yield_dates_all)
        if isinstance(value, (int, float)) and value > 0 and _is_iso_date_string(row_date)
    ]
    yield_value = [value for value, _row_date in yield_pairs]
    yield_dates = [row_date for _value, row_date in yield_pairs]

    quant = _quant_config()
    intraday_pctl_lookback = (
        lookback_selected if lookback_selected is not None else quant["intraday_pctl_lookback"]
    )
    trend_lookback = lookback_selected if lookback_selected is not None else quant["trend_lookback"]
    series_min = quant["series_min_bars"]
    series_target = quant["series_target_bars"]
    vix_title = (
        f"Intraday Volatility Proxy State ({used_vix_ticker})"
        if _is_proxy_vix_ticker(used_vix_ticker)
        else "Intraday VIX State"
    )

    return [
        {
            "id": "intraday_spy_state",
            "title": "Intraday SPY State",
            "series": spy_close,
            "series_dates": spy_dates,
            "lookback": intraday_pctl_lookback,
            "trend_lookback": trend_lookback,
            "series_target": series_target,
            "series_min": series_min,
            "lookback_selected": lookback_selected,
        },
        {
            "id": "intraday_vix_state",
            "title": vix_title,
            "series": vix_close,
            "series_dates": vix_dates,
            "lookback": intraday_pctl_lookback,
            "trend_lookback": trend_lookback,
            "series_target": series_target,
            "series_min": series_min,
            "lookback_selected": lookback_selected,
        },
        {
            "id": "intraday_yield_state",
            "title": "Intraday 10Y Yield State",
            "series": yield_value,
            "series_dates": yield_dates,
            "lookback": intraday_pctl_lookback,
            "trend_lookback": trend_lookback,
            "series_target": series_target,
            "series_min": series_min,
            "lookback_selected": lookback_selected,
        },
    ]


def _rows_to_close_map(rows: list[dict]) -> dict[str, float]:
    out: dict[str, float] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_date = row.get("date")
        close = row.get("close")
        if _is_iso_date_string(row_date) and isinstance(close, (int, float)) and close > 0:
            out[row_date] = float(close)
    return out


def _build_log_ratio_series(rows_a: list[dict], rows_b: list[dict]) -> tuple[list[float], list[str]]:
    a_by_date = _rows_to_close_map(rows_a)
    b_by_date = _rows_to_close_map(rows_b)
    common_dates = sorted(set(a_by_date.keys()) & set(b_by_date.keys()))
    series: list[float] = []
    series_dates: list[str] = []
    for row_date in common_dates:
        a_close = a_by_date.get(row_date)
        b_close = b_by_date.get(row_date)
        if not isinstance(a_close, float) or not isinstance(b_close, float):
            continue
        if a_close <= 0 or b_close <= 0:
            continue
        series.append(math.log(a_close / b_close))
        series_dates.append(row_date)
    return series, series_dates


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
    series_dates: list[str] | None,
    trend_lookback: int,
    pctl_lookback: int,
    series_target: int,
    series_min: int,
    data_note: str | None = None,
    lookback_selected: int | None = None,
) -> dict:
    timestamp = _iso_now()
    status = "ok"
    latest = None
    percentile = None
    regime = None
    slope = None
    trend_direction = None
    had_error = False

    min_required_points = max(series_min, pctl_lookback + 1, trend_lookback)
    if len(series) < min_required_points:
        status = "partial"
    else:
        try:
            latest = round(series[-1], 6)
            percentile_raw = rolling_percentile(series, lookback=pctl_lookback)
            if percentile_raw is None:
                status = "partial"
            else:
                percentile = round(percentile_raw, 2)
                regime = classify_regime(percentile)
        except ValueError:
            status = "partial"
        except Exception:
            had_error = True

        try:
            trend_window = series[-trend_lookback:]
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

    sparkline, sparkline_times = _panel_sparkline_with_times(series, series_dates)

    panel = {
        "id": panel_id,
        "title": title,
        "raw_metrics": raw_metrics,
        "sparkline": sparkline,
        "sparkline_times": sparkline_times,
        "context": [],
        "interpretation": [],
        "why_toggle": "",
        "status": status,
        "last_updated": timestamp,
        "window_meta": {
            "series_points": len(series),
            "series_target": series_target,
            "series_min": series_min,
            "pctl_lookback": pctl_lookback,
            "trend_lookback": trend_lookback,
            "pctl_excludes_current": True,
        },
    }
    if lookback_selected is not None:
        panel["window_meta"]["lookback_selected"] = lookback_selected

    generated = generate_interpretation("swing", panel)
    panel["context"] = generated["context"]
    panel["interpretation"] = generated["interpretation"]
    panel["why_toggle"] = generated["why_toggle"]

    if status == "partial" and isinstance(data_note, str) and data_note:
        panel["interpretation"].append(guard_language(f"Data note: {data_note}"))

    return panel


def _build_swing_panels(conn, lookback_selected: int | None = None) -> list[dict]:
    breadth_a = os.getenv("MEI_SWING_BREADTH_A", "RSP")
    breadth_b = os.getenv("MEI_SWING_BREADTH_B", "SPY")
    conc_a = os.getenv("MEI_SWING_CONC_A", "QQQ")
    conc_b = os.getenv("MEI_SWING_CONC_B", "SPY")
    sent_a = os.getenv("MEI_SWING_SENT_A", "HYG")
    sent_b = os.getenv("MEI_SWING_SENT_B", "SHY")
    swing_vix = os.getenv("MEI_SWING_VIX_TICKER", "I:VIX")
    swing_vol_etf = os.getenv("MEI_SWING_VOL_ETF", "VXX")
    quant = _quant_config()
    trend_lookback = lookback_selected if lookback_selected is not None else quant["trend_lookback"]
    pctl_lookback = (
        lookback_selected if lookback_selected is not None else quant["swing_pctl_lookback"]
    )
    series_target = quant["series_target_bars"]
    series_min = quant["series_min_bars"]

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
    breadth_series, breadth_dates = _build_log_ratio_series(breadth_a_rows, breadth_b_rows)
    conc_series, conc_dates = _build_log_ratio_series(conc_a_rows, conc_b_rows)
    sent_series, sent_dates = _build_log_ratio_series(sent_a_rows, sent_b_rows)
    vol_series, vol_dates = _build_log_ratio_series(vol_rows, vix_rows)

    panels = [
        _build_swing_proxy_panel(
            panel_id="swing_breadth_participation",
            title="Swing Breadth Participation",
            source_tickers=f"{breadth_a}/{breadth_b}",
            series=breadth_series,
            series_dates=breadth_dates,
            trend_lookback=trend_lookback,
            pctl_lookback=pctl_lookback,
            series_target=series_target,
            series_min=series_min,
            data_note=breadth_note,
            lookback_selected=lookback_selected,
        ),
        _build_swing_proxy_panel(
            panel_id="swing_concentration_tilt",
            title="Swing Concentration Tilt",
            source_tickers=f"{conc_a}/{conc_b}",
            series=conc_series,
            series_dates=conc_dates,
            trend_lookback=trend_lookback,
            pctl_lookback=pctl_lookback,
            series_target=series_target,
            series_min=series_min,
            data_note=conc_note,
            lookback_selected=lookback_selected,
        ),
        _build_swing_proxy_panel(
            panel_id="swing_risk_sentiment",
            title="Swing Risk Sentiment",
            source_tickers=f"{sent_a}/{sent_b}",
            series=sent_series,
            series_dates=sent_dates,
            trend_lookback=trend_lookback,
            pctl_lookback=pctl_lookback,
            series_target=series_target,
            series_min=series_min,
            data_note=sent_note,
            lookback_selected=lookback_selected,
        ),
        _build_swing_proxy_panel(
            panel_id="swing_vol_term_structure",
            title="Swing Volatility Term Structure Proxy",
            source_tickers=f"{swing_vol_etf}/{swing_vix}",
            series=vol_series,
            series_dates=vol_dates,
            trend_lookback=trend_lookback,
            pctl_lookback=pctl_lookback,
            series_target=series_target,
            series_min=series_min,
            data_note=vol_combined_note,
            lookback_selected=lookback_selected,
        ),
    ]
    return panels


def _build_swing_payload(conn, lookback_selected: int | None = None) -> dict:
    panels = _build_swing_panels(conn, lookback_selected=lookback_selected)
    return _build_payload_from_panels("swing", panels, lookback_selected=lookback_selected)


@app.get("/api/intraday")
def get_intraday(lookback: int | None = None):
    lookback_selected = _resolve_selected_lookback(lookback)
    return _build_with_persistence(
        tab="intraday",
        panel_specs_builder=_build_intraday_panel_specs,
        lookback_selected=lookback_selected,
    )


@app.get("/api/swing")
def get_swing(lookback: int | None = None):
    lookback_selected = _resolve_selected_lookback(lookback)
    return _build_with_persistence(
        tab="swing",
        payload_builder=_build_swing_payload,
        lookback_selected=lookback_selected,
    )


def _build_with_persistence(
    tab: str,
    panel_specs: list[dict] | None = None,
    panel_specs_builder=None,
    payload_builder=None,
    lookback_selected: int | None = None,
) -> dict:
    forced_fail_tab = os.getenv("MEI_FORCE_FAIL_TAB", "").strip().lower()
    try:
        if forced_fail_tab == tab:
            raise RuntimeError("forced failure")

        conn = connect()
        try:
            init_db(conn)
            if payload_builder is not None:
                try:
                    payload = payload_builder(conn, lookback_selected=lookback_selected)
                except TypeError:
                    payload = payload_builder(conn)
            else:
                specs = panel_specs if panel_specs is not None else []
                if panel_specs_builder is not None:
                    try:
                        specs = panel_specs_builder(conn, lookback_selected=lookback_selected)
                    except TypeError:
                        specs = panel_specs_builder(conn)
                payload = build_payload(tab, specs, lookback_selected=lookback_selected)
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
