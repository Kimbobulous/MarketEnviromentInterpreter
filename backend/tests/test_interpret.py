from backend.lib.interpret import (
    BANNED_PHRASES,
    detect_tensions,
    generate_interpretation,
    guard_language,
)
from backend.main import get_intraday, get_swing


def _assert_no_banned_phrases(text: str):
    lowered = f" {text.lower()} "
    for phrase in BANNED_PHRASES:
        assert phrase.lower() not in lowered


def test_guard_language_softens_will_and_prediction_words():
    source = "This will definitely predict a move and guarantee certainty."
    cleaned = guard_language(source)
    assert "will" not in cleaned.lower()
    assert "definitely" not in cleaned.lower()
    assert "predict" not in cleaned.lower()
    assert "guarantee" not in cleaned.lower()
    _assert_no_banned_phrases(cleaned)


def test_generate_interpretation_ok_status_returns_non_empty_and_guarded_text():
    panel = {
        "status": "ok",
        "raw_metrics": [
            {"key": "percentile_lookback", "value": 72.5, "unit": ""},
            {"key": "regime", "value": "High", "unit": ""},
            {"key": "trend_slope", "value": 0.0132, "unit": ""},
            {"key": "trend_direction", "value": "Up", "unit": ""},
        ],
    }

    out = generate_interpretation("intraday", panel)
    assert out["context"]
    assert out["interpretation"]
    assert out["why_toggle"]

    for line in out["context"]:
        _assert_no_banned_phrases(line)
    for line in out["interpretation"]:
        _assert_no_banned_phrases(line)
    _assert_no_banned_phrases(out["why_toggle"])


def test_generate_interpretation_partial_mentions_insufficient_history():
    panel = {
        "status": "partial",
        "raw_metrics": [
            {"key": "percentile_lookback", "value": None, "unit": ""},
            {"key": "regime", "value": None, "unit": ""},
            {"key": "trend_slope", "value": None, "unit": ""},
            {"key": "trend_direction", "value": None, "unit": ""},
        ],
    }

    out = generate_interpretation("intraday", panel)
    combined = " ".join(out["context"] + out["interpretation"]).lower()
    assert "insufficient history" in combined

    for line in out["context"]:
        _assert_no_banned_phrases(line)
    for line in out["interpretation"]:
        _assert_no_banned_phrases(line)
    _assert_no_banned_phrases(out["why_toggle"])


def test_detect_tensions_high_down_is_severity_three():
    tensions = detect_tensions(
        {"regime": "High", "trend_direction": "Down", "trend_slope": -0.01, "percentile": 85}
    )
    assert tensions
    assert any(item["severity"] >= 3 for item in tensions)


def test_detect_tensions_low_up_has_at_least_severity_one():
    tensions = detect_tensions(
        {"regime": "Low", "trend_direction": "Up", "trend_slope": 0.01, "percentile": 20}
    )
    assert tensions
    assert any(item["severity"] >= 1 for item in tensions)


def test_detect_tensions_unknown_trend_has_unavailable_message():
    tensions = detect_tensions(
        {
            "regime": "Mid",
            "trend_direction": "Unknown",
            "trend_slope": None,
            "percentile": 50,
        }
    )
    labels = {item["label"] for item in tensions}
    assert "Trend unavailable" in labels


def _assert_panel_generated_text_and_guardrails(panel):
    assert isinstance(panel["context"], list) and panel["context"]
    assert isinstance(panel["interpretation"], list) and panel["interpretation"]
    assert panel["why_toggle"]

    for line in panel["context"]:
        _assert_no_banned_phrases(line)
    for line in panel["interpretation"]:
        _assert_no_banned_phrases(line)
    if isinstance(panel["why_toggle"], list):
        for line in panel["why_toggle"]:
            _assert_no_banned_phrases(line)
    else:
        _assert_no_banned_phrases(panel["why_toggle"])


def test_all_intraday_and_swing_panels_use_generated_interpretation_and_guardrails():
    intraday_payload = get_intraday()
    swing_payload = get_swing()

    for panel in intraday_payload["panels"]:
        _assert_panel_generated_text_and_guardrails(panel)

    for panel in swing_payload["panels"]:
        _assert_panel_generated_text_and_guardrails(panel)


def test_payload_tension_lines_if_present_are_guarded():
    for payload in (get_intraday(), get_swing()):
        for panel in payload["panels"]:
            tension_lines = [
                line
                for line in panel["interpretation"]
                if isinstance(line, str) and "Tension:" in line
            ]
            for line in tension_lines:
                _assert_no_banned_phrases(line)


def test_intraday_interpretation_mentions_latest_regime_and_trend():
    panel = {
        "status": "ok",
        "raw_metrics": [
            {"key": "latest_value", "value": 472.55, "unit": ""},
            {"key": "percentile_lookback", "value": 84.0, "unit": ""},
            {"key": "regime", "value": "High", "unit": ""},
            {"key": "trend_slope", "value": 0.0123, "unit": ""},
            {"key": "trend_direction", "value": "Up", "unit": ""},
        ],
    }

    out = generate_interpretation("intraday", panel)
    combined = " ".join(out["context"] + out["interpretation"]).lower()

    assert "latest observed value" in combined
    assert "percentile" in combined
    assert "regime" in combined
    assert "trend state" in combined
    assert "slope" in combined

    for line in out["context"]:
        _assert_no_banned_phrases(line)
    for line in out["interpretation"]:
        _assert_no_banned_phrases(line)
    _assert_no_banned_phrases(out["why_toggle"])
