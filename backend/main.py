from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.lib.compute import classify_regime, rolling_percentile, trend_slope
from backend.lib.interpret import (
    detect_tensions,
    extract_signals,
    generate_interpretation,
    guard_language,
)

app = FastAPI()

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
