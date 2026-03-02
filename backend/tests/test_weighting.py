from backend.lib.interpret import BANNED_PHRASES
from backend.lib.weighting import (
    build_structured_summary,
    classify_summary,
    map_panel_to_force,
    score_forces,
)


def _panel(panel_id: str, regime: str, trend: str, status: str = "ok") -> dict:
    return {
        "id": panel_id,
        "status": status,
        "raw_metrics": [
            {"key": "regime", "value": regime, "unit": ""},
            {"key": "trend_direction", "value": trend, "unit": ""},
        ],
    }


def _assert_no_banned_phrases(text: str):
    lowered = f" {text.lower()} "
    for phrase in BANNED_PHRASES:
        assert phrase.lower() not in lowered


def test_map_panel_to_force_returns_expected_for_known_ids():
    assert map_panel_to_force("intraday", "intraday_vix_state") == "volatility"
    assert map_panel_to_force("intraday", "intraday_yield_state") == "rates"
    assert map_panel_to_force("intraday", "intraday_spy_state") == "concentration"

    assert map_panel_to_force("swing", "swing_breadth_participation") == "breadth"
    assert map_panel_to_force("swing", "swing_concentration_tilt") == "concentration"
    assert map_panel_to_force("swing", "swing_risk_sentiment") == "sentiment"
    assert map_panel_to_force("swing", "swing_vol_term_structure") == "volatility"

    assert map_panel_to_force("intraday", "unknown_panel") is None


def test_score_forces_high_up_ok_beats_low_down_partial():
    high_up_ok = score_forces(
        "intraday",
        [
            _panel("intraday_vix_state", "High", "Up", "ok"),
        ],
    )
    low_down_partial = score_forces(
        "intraday",
        [
            _panel("intraday_vix_state", "Low", "Down", "partial"),
        ],
    )

    assert high_up_ok["volatility"] > low_down_partial["volatility"]


def test_score_forces_clamps_to_non_negative():
    scores = score_forces(
        "intraday",
        [
            _panel("intraday_vix_state", "Low", "Down", "error"),
        ],
    )

    assert scores["volatility"] >= 0.0


def test_classify_summary_strong_moderate_mixed_thresholds():
    strong = classify_summary(
        {"volatility": 0.72, "rates": 0.30, "concentration": 0.15},
        tension_panels=0,
    )
    moderate = classify_summary(
        {"volatility": 0.50, "rates": 0.35, "concentration": 0.10},
        tension_panels=0,
    )
    mixed = classify_summary(
        {"volatility": 0.41, "rates": 0.36, "concentration": 0.34},
        tension_panels=0,
    )

    assert strong["strength"] == "strong"
    assert moderate["strength"] == "moderate"
    assert mixed["strength"] == "mixed"


def test_build_structured_summary_shape_and_guardrails():
    summary = build_structured_summary(
        "intraday",
        {
            "dominant_force": "volatility",
            "strength": "strong",
            "mixed_leadership": False,
            "tension_panels": 0,
            "sorted_forces": [
                ("volatility", 0.72),
                ("rates", 0.40),
                ("concentration", 0.33),
            ],
        },
    )

    assert 3 <= len(summary) <= 4
    assert summary[0].startswith("Lead:")
    assert summary[1].startswith("Support:")

    for line in summary:
        _assert_no_banned_phrases(line)


def test_mixed_leadership_summary_line_when_top_scores_are_close_and_tensions_exist():
    force_summary = classify_summary(
        {"volatility": 0.55, "concentration": 0.50, "rates": 0.21},
        tension_panels=2,
    )
    summary = build_structured_summary("intraday", force_summary)
    mixed_line = next((line for line in summary if line.startswith("Mixed signals:")), "")
    assert mixed_line
