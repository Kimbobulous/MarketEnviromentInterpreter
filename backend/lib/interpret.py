"""Template-driven interpretation helpers with language guardrails."""

import re

BANNED_PHRASES = [
    " will ",
    " going to ",
    " guarantee",
    " guaranteed",
    " predict",
    " prediction",
    " certainly",
    " definitely",
    " sure thing",
]


def guard_language(text: str) -> str:
    """Return a softened version of text that avoids banned phrasing."""
    if not isinstance(text, str):
        return ""

    cleaned = text
    replacements = [
        (r"\bgoing to\b", "may"),
        (r"\bwill\b", "may"),
        (r"\bguaranteed\b", "suggests"),
        (r"\bguarantee\b", "suggests"),
        (r"\bprediction\b", "indicates"),
        (r"\bpredict\b", "indicates"),
        (r"\bcertainly\b", "likely"),
        (r"\bdefinitely\b", "likely"),
        (r"\bsure thing\b", "likely"),
    ]

    for pattern, replacement in replacements:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def metric_lookup(raw_metrics: list[dict], key: str):
    """Return first metric value where metric.key matches key."""
    if not isinstance(raw_metrics, list):
        return None

    for metric in raw_metrics:
        if isinstance(metric, dict) and metric.get("key") == key:
            return metric.get("value")
    return None


def extract_signals(panel: dict) -> dict:
    """Extract normalized regime/trend signals from panel raw metrics."""
    safe_panel = panel if isinstance(panel, dict) else {}
    raw_metrics = safe_panel.get("raw_metrics", [])
    if not isinstance(raw_metrics, list):
        raw_metrics = []

    percentile = None
    for metric in raw_metrics:
        if isinstance(metric, dict) and str(metric.get("key", "")).startswith("percentile"):
            percentile = metric.get("value")
            break

    regime = metric_lookup(raw_metrics, "regime")
    trend_direction = metric_lookup(raw_metrics, "trend_direction")
    trend_slope = metric_lookup(raw_metrics, "trend_slope")

    if not isinstance(regime, str) or not regime:
        regime = "Unknown"
    if not isinstance(trend_direction, str) or not trend_direction:
        trend_direction = "Unknown"
    if not isinstance(trend_slope, (int, float)):
        trend_slope = None

    return {
        "regime": regime,
        "trend_direction": trend_direction,
        "trend_slope": trend_slope,
        "percentile": percentile,
    }


def detect_tensions(signals: dict) -> list[dict]:
    """Return deterministic tension list based on regime/trend conflicts."""
    regime = signals.get("regime", "Unknown")
    trend = signals.get("trend_direction", "Unknown")
    slope = signals.get("trend_slope")

    tensions = []

    if regime == "High" and trend == "Down":
        tensions.append(
            {
                "label": "High+Down",
                "severity": 3,
                "message": "High regime is paired with a Down trend signal.",
            }
        )
    if regime == "High" and trend == "Flat":
        tensions.append(
            {
                "label": "High+Flat",
                "severity": 2,
                "message": "High regime is paired with a Flat trend signal.",
            }
        )
    if regime == "Low" and trend == "Up":
        tensions.append(
            {
                "label": "Low+Up",
                "severity": 1,
                "message": "Low regime is paired with an Up trend signal.",
            }
        )
    if regime == "Mid" and trend == "Down":
        severity = 2 if isinstance(slope, (int, float)) and slope < -0.005 else 1
        tensions.append(
            {
                "label": "Mid+Down",
                "severity": severity,
                "message": "Mid regime is paired with a Down trend signal.",
            }
        )
    if trend == "Unknown":
        tensions.append(
            {
                "label": "Trend unavailable",
                "severity": 1,
                "message": "Trend signal is unavailable.",
            }
        )

    return tensions


def generate_interpretation(tab_name: str, panel: dict) -> dict:
    """Generate context, interpretation, and why_toggle for a panel."""
    safe_panel = panel if isinstance(panel, dict) else {}
    signals = extract_signals(safe_panel)

    percentile = signals["percentile"]
    regime = signals["regime"]
    trend_direction = signals["trend_direction"]
    trend_slope = signals["trend_slope"]
    status = safe_panel.get("status")
    tensions = detect_tensions(signals)

    if status == "partial":
        context = ["Some metrics unavailable due to insufficient history."]
        interpretation = [
            f"{tab_name.capitalize()} panel is in partial state with descriptive-only context."
        ]
        why_toggle = (
            "When history is short or incomplete, the panel emphasizes current state "
            "description rather than a stronger directional framing."
        )
    else:
        context = [
            (
                f"{tab_name.capitalize()} panel shows regime={regime} and trend="
                f"{trend_direction} (slope={trend_slope})."
            ),
            f"Percentile positioning is {percentile} relative to recent history.",
        ]
        interpretation = [
            (
                f"Current regime is {regime} with {trend_direction} trend; "
                "this reflects recent positioning relative to history."
            )
        ]
        why_toggle = (
            "Regime and trend combine to frame current risk posture in descriptive terms. "
            "Changes in either metric can shift how conditions are characterized."
        )

    if tensions:
        ordered = sorted(tensions, key=lambda item: (-item["severity"], item["label"]))
        top_messages = [item["message"] for item in ordered[:2]]
        interpretation.append(f"Tension: {' '.join(top_messages)}")
        context.append("Note: Mixed signals present; interpret regime and trend jointly.")

    guarded_context = [guard_language(line) for line in context if isinstance(line, str)]
    guarded_interpretation = [
        guard_language(line) for line in interpretation if isinstance(line, str)
    ]

    if isinstance(why_toggle, list):
        guarded_why = [guard_language(line) for line in why_toggle if isinstance(line, str)]
    else:
        guarded_why = guard_language(str(why_toggle))

    return {
        "context": guarded_context,
        "interpretation": guarded_interpretation,
        "why_toggle": guarded_why,
    }
