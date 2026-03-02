"""Deterministic force-weighting helpers for tab-level summary synthesis."""

from __future__ import annotations

from typing import Iterable

from .interpret import guard_language

INTRADAY_BASE_WEIGHTS = {
    "volatility": 0.40,
    "rates": 0.30,
    "concentration": 0.30,
}

SWING_BASE_WEIGHTS = {
    "breadth": 0.30,
    "concentration": 0.25,
    "sentiment": 0.25,
    "volatility": 0.20,
}

REGIME_SCORES = {
    "high": 1.0,
    "mid": 0.6,
    "low": 0.3,
}

DIRECTIONAL_MODIFIERS = {
    "up": 0.2,
    "flat": 0.0,
    "down": -0.2,
    "unknown": 0.0,
}

CONFIDENCE_MODIFIERS = {
    "ok": 1.0,
    "partial": 0.6,
    "error": 0.0,
}

FORCE_KEYWORDS = ["volatility", "rates", "breadth", "concentration", "sentiment"]


def map_panel_to_force(tab: str, panel_id: str) -> str | None:
    """Map panel ids into standardized force categories."""
    tab_key = str(tab or "").strip().lower()
    panel_key = str(panel_id or "").strip()

    intraday = {
        "intraday_vix_state": "volatility",
        "intraday_yield_state": "rates",
        "intraday_spy_state": "concentration",
    }
    swing = {
        "swing_breadth_participation": "breadth",
        "swing_concentration_tilt": "concentration",
        "swing_risk_sentiment": "sentiment",
        "swing_vol_term_structure": "volatility",
    }

    if tab_key == "intraday":
        return intraday.get(panel_key)
    if tab_key == "swing":
        return swing.get(panel_key)
    return None


def extract_panel_signals(panel: dict) -> dict:
    """Extract normalized regime/trend/status signals from a panel."""
    safe_panel = panel if isinstance(panel, dict) else {}
    raw_metrics = safe_panel.get("raw_metrics")
    if not isinstance(raw_metrics, list):
        raw_metrics = []

    regime = "Unknown"
    trend_direction = "Unknown"

    for metric in raw_metrics:
        if not isinstance(metric, dict):
            continue
        key = str(metric.get("key", "")).strip()
        value = metric.get("value")
        if key == "regime" and isinstance(value, str) and value.strip():
            regime = value.strip()
        elif key == "trend_direction" and isinstance(value, str) and value.strip():
            trend_direction = value.strip()

    status = safe_panel.get("status")
    if not isinstance(status, str) or not status.strip():
        status = "partial"

    return {
        "regime": regime,
        "trend_direction": trend_direction,
        "status": status.lower(),
    }


def score_forces(tab: str, panels: list[dict]) -> dict:
    """Compute deterministic weighted scores per force for a tab."""
    tab_key = str(tab or "").strip().lower()
    base_weights = _base_weights_for_tab(tab_key)
    scores = {force: 0.0 for force in base_weights.keys()}

    for panel in panels if isinstance(panels, list) else []:
        if not isinstance(panel, dict):
            continue

        force = map_panel_to_force(tab_key, panel.get("id", ""))
        if force is None:
            continue

        base_weight = base_weights.get(force, 0.0)
        signals = extract_panel_signals(panel)

        regime_score = REGIME_SCORES.get(str(signals["regime"]).lower(), 0.0)
        directional_modifier = DIRECTIONAL_MODIFIERS.get(
            str(signals["trend_direction"]).lower(), 0.0
        )
        confidence_modifier = CONFIDENCE_MODIFIERS.get(str(signals["status"]).lower(), 0.0)

        raw_score = (
            base_weight * regime_score * confidence_modifier
            + (base_weight * directional_modifier)
        )
        panel_score = _clamp(raw_score, minimum=0.0, maximum=1.5)
        scores[force] = round(scores.get(force, 0.0) + panel_score, 4)

    return scores


def classify_summary(force_scores: dict, tension_panels: int) -> dict:
    """Classify dominant force and leadership shape from force scores."""
    safe_scores = force_scores if isinstance(force_scores, dict) else {}
    normalized_scores = {
        str(force): float(score)
        for force, score in safe_scores.items()
        if isinstance(score, (int, float))
    }

    sorted_forces = sorted(
        normalized_scores.items(),
        key=lambda item: (-item[1], item[0]),
    )

    top_force, top_score = sorted_forces[0] if sorted_forces else ("unknown", 0.0)
    _, second_score = sorted_forces[1] if len(sorted_forces) > 1 else ("unknown", 0.0)
    margin = top_score - second_score

    if top_score >= 0.60 and margin >= 0.15:
        strength = "strong"
    elif top_score >= 0.40 and margin >= 0.10:
        strength = "moderate"
    else:
        strength = "mixed"

    close_to_top = [
        force
        for force, score in sorted_forces
        if abs(top_score - score) <= 0.10
    ]

    return {
        "dominant_force": top_force,
        "strength": strength,
        "top_score": round(top_score, 4),
        "second_score": round(second_score, 4),
        "mixed_leadership": len(close_to_top) >= 2,
        "tension_panels": int(tension_panels),
        "sorted_forces": [(force, round(score, 4)) for force, score in sorted_forces],
    }


def build_structured_summary(tab: str, force_summary: dict) -> list[str]:
    """Build guardrailed 3-4 sentence weighted summary lines."""
    _ = tab
    safe = force_summary if isinstance(force_summary, dict) else {}
    sorted_forces = safe.get("sorted_forces")
    if not isinstance(sorted_forces, list):
        sorted_forces = []

    dominant = str(safe.get("dominant_force", "unknown"))
    strength = str(safe.get("strength", "mixed"))

    support_forces = _support_forces(sorted_forces)
    mixed_leadership = bool(safe.get("mixed_leadership", False))
    tension_panels = int(safe.get("tension_panels", 0))

    lines = [
        guard_language(
            f"Lead: {dominant} is the dominant driver ({strength}), based on current panel signals."
        ),
        guard_language(
            f"Support: Next influences are {support_forces[0]}, {support_forces[1]} (ordered)."
        ),
    ]

    if mixed_leadership or tension_panels > 0:
        lines.append(
            guard_language(
                "Mixed signals: leadership is shared across multiple forces; interpret signals jointly."
            )
        )
    else:
        lines.append(
            guard_language(
                "Signal balance: leadership is relatively concentrated in the top factor."
            )
        )

    lines.append(
        guard_language(
            "Scope: Summary reflects computed regime/trend states and does not project outcomes."
        )
    )

    return lines


def _support_forces(sorted_forces: list[tuple[str, float]]) -> tuple[str, str]:
    names = [force for force, _score in sorted_forces if isinstance(force, str) and force]
    first = names[1] if len(names) > 1 else "none"
    second = names[2] if len(names) > 2 else "none"
    return first, second


def _base_weights_for_tab(tab: str) -> dict[str, float]:
    if tab == "intraday":
        return INTRADAY_BASE_WEIGHTS
    if tab == "swing":
        return SWING_BASE_WEIGHTS
    return {}


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def contains_force_keyword(lines: Iterable[str]) -> bool:
    """Helper for tests/diagnostics to detect force keyword presence."""
    lowered = " ".join(str(line).lower() for line in lines if isinstance(line, str))
    return any(keyword in lowered for keyword in FORCE_KEYWORDS)
