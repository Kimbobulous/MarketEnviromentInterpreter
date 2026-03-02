from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.lib.compute import classify_regime, rolling_percentile, trend_slope

app = FastAPI()

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


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def panel_status(percentile, slope):
    if percentile is None or slope is None:
        return "partial"
    return "ok"


def _compute_outputs(series: list[float], lookback: int) -> dict:
    percentile = None
    regime = None
    slope = None
    trend_direction = None
    had_error = False

    try:
        percentile = round(rolling_percentile(series, lookback=lookback), 2)
        regime = classify_regime(percentile)
    except ValueError:
        percentile = None
        regime = None
    except Exception:
        had_error = True

    try:
        slope = round(trend_slope(series), 4)
        trend_direction = "Up" if slope > 0 else "Down" if slope < 0 else "Flat"
    except ValueError:
        slope = None
        trend_direction = None
    except Exception:
        had_error = True

    status = "error" if had_error else panel_status(percentile, slope)

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
        {"key": "percentile_lookback", "value": percentile, "unit": ""},
        {"key": "regime", "value": regime, "unit": ""},
        {"key": "trend_slope", "value": slope, "unit": ""},
        {"key": "trend_direction", "value": trend_direction, "unit": ""},
    ]

    if status == "ok":
        context = [
            f"Regime bucket is {regime} from lookback percentile {percentile}.",
            f"Trend direction is {trend_direction} with slope {slope}.",
        ]
        interpretation = [
            f"{tab_name.capitalize()} regime is {regime} with {trend_direction} trend."
        ]
        why_toggle = (
            f"Percentile over {lookback} prior observations and log-slope trend are used "
            "to classify the current environment state."
        )
    elif status == "partial":
        context = [
            "Some compute inputs are insufficient for full state classification.",
            f"Lookback={lookback}, history_length={len(series)}.",
        ]
        interpretation = ["Insufficient history for trend or percentile; state is partial."]
        why_toggle = (
            "A partial state occurs when lookback history or valid positive values are not "
            "available for all compute metrics."
        )
    else:
        context = ["A compute exception occurred while deriving this panel."]
        interpretation = ["Compute error prevented full classification; state is error."]
        why_toggle = "Unexpected compute errors are surfaced as error status for transparency."

    return {
        "id": panel_id,
        "title": title,
        "raw_metrics": raw_metrics,
        "context": context,
        "interpretation": interpretation,
        "why_toggle": why_toggle,
        "status": status,
        "last_updated": timestamp,
    }


def _extract_metric_value(panel: dict, key: str):
    for metric in panel.get("raw_metrics", []):
        if metric.get("key") == key:
            return metric.get("value")
    return None


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
    regime_counts = {"Low": 0, "Mid": 0, "High": 0}
    trend_counts = {"Up": 0, "Down": 0, "Flat": 0}

    for panel in panels:
        regime = _extract_metric_value(panel, "regime")
        if regime in regime_counts:
            regime_counts[regime] += 1

        trend_direction = _extract_metric_value(panel, "trend_direction")
        if trend_direction in trend_counts:
            trend_counts[trend_direction] += 1

    conditional_sensitivity = [
        (
            f"If more panels shift to High regime (currently {regime_counts['High']}/"
            f"{panel_count}), dispersion assumptions would likely become wider."
        ),
        (
            f"If Up trends ({trend_counts['Up']}/{panel_count}) reverse toward Down "
            "or Flat, directional interpretation would weaken."
        ),
        (
            f"If partial panels ({status_counts['partial']}/{panel_count}) gain enough history, "
            "state confidence should improve."
        ),
    ]

    summary = [
        f"{tab_name.capitalize()} has {status_counts['ok']}/{panel_count} panels in ok status "
        f"({status_counts['partial']} partial, {status_counts['error']} error).",
        (
            f"Regime mix: Low {regime_counts['Low']}, Mid {regime_counts['Mid']}, "
            f"High {regime_counts['High']}."
        ),
        (
            f"Trend mix: Up {trend_counts['Up']}, Down {trend_counts['Down']}, "
            f"Flat {trend_counts['Flat']}."
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
        "endpoints": ["/api/intraday", "/api/swing", "/health"],
    }


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/intraday")
def get_intraday():
    panel_specs = [
        {
            "id": "intraday_vol_state",
            "title": "Intraday Volatility State",
            "series": [
                1.00,
                1.02,
                1.01,
                1.03,
                1.04,
                1.05,
                1.04,
                1.06,
                1.07,
                1.08,
                1.09,
                1.10,
                1.11,
                1.10,
                1.12,
                1.13,
                1.14,
                1.15,
                1.16,
                1.17,
                1.20,
            ],
            "lookback": 20,
        }
    ]
    return build_payload("intraday", panel_specs)


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
    return build_payload("swing", panel_specs)
