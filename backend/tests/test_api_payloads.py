import re

from backend.lib.interpret import BANNED_PHRASES
from backend.lib.weighting import contains_force_keyword
from backend.main import _build_panel, get_intraday, get_swing


TOP_LEVEL_KEYS = {
    "tab",
    "last_updated",
    "panels",
    "conditional_sensitivity",
    "summary",
}

PANEL_KEYS = {
    "id",
    "title",
    "raw_metrics",
    "sparkline",
    "sparkline_times",
    "context",
    "interpretation",
    "why_toggle",
    "status",
    "last_updated",
}

WINDOW_META_KEYS = {
    "series_points",
    "series_target",
    "series_min",
    "pctl_lookback",
    "trend_lookback",
    "pctl_excludes_current",
}

COMPUTE_METRIC_KEYS = {
    "percentile_lookback",
    "regime",
    "trend_slope",
    "trend_direction",
}


def _assert_payload_contract(payload):
    assert set(payload.keys()) == TOP_LEVEL_KEYS
    assert isinstance(payload["panels"], list) and payload["panels"]
    assert isinstance(payload["conditional_sensitivity"], list)
    assert isinstance(payload["summary"], list)

    for panel in payload["panels"]:
        assert PANEL_KEYS <= set(panel.keys())
        assert panel["status"] in {"ok", "partial", "error"}
        metric_keys = {metric.get("key") for metric in panel["raw_metrics"]}
        assert COMPUTE_METRIC_KEYS <= metric_keys
        assert isinstance(panel["sparkline"], list)
        assert isinstance(panel["sparkline_times"], list)
        assert len(panel["sparkline_times"]) == len(panel["sparkline"])
        assert len(panel["sparkline_times"]) <= 60
        assert len(panel["sparkline"]) <= 60
        assert all(isinstance(value, (int, float)) for value in panel["sparkline"])
        assert all(isinstance(value, str) for value in panel["sparkline_times"])
        assert all(re.match(r"^\d{4}-\d{2}-\d{2}$", value) for value in panel["sparkline_times"])
        assert WINDOW_META_KEYS <= set(panel.get("window_meta", {}).keys())


def _assert_no_banned_phrases(text: str):
    lowered = f" {text.lower()} "
    for phrase in BANNED_PHRASES:
        assert phrase.lower() not in lowered


def _extract_counts(line: str) -> list[int]:
    return [int(match) for match in re.findall(r"=(\d+)", line)]


def _compute_metric_map(panel):
    return {metric.get("key"): metric.get("value") for metric in panel["raw_metrics"]}


def test_intraday_payload_contract_and_compute_fields():
    payload = get_intraday()
    assert payload["tab"] == "intraday"
    _assert_payload_contract(payload)


def test_swing_payload_contract_and_compute_fields():
    payload = get_swing()
    assert payload["tab"] == "swing"
    _assert_payload_contract(payload)


def test_panel_partial_status_when_lookback_exceeds_history():
    panel = _build_panel(
        panel_id="test_partial",
        title="Test Partial Panel",
        series=[1.0, 1.1, 1.2],
        lookback=20,
        timestamp="2026-03-02T00:00:00+00:00",
    )

    assert panel["status"] == "partial"
    metric_by_key = {metric["key"]: metric["value"] for metric in panel["raw_metrics"]}
    assert metric_by_key["percentile_lookback"] is None
    assert metric_by_key["regime"] is None
    combined_text = " ".join(panel["context"] + panel["interpretation"]).lower()
    assert "insufficient history" in combined_text or "partial state" in combined_text


def test_intraday_compute_outputs_are_deterministic_between_calls():
    payload_a = get_intraday()
    payload_b = get_intraday()

    _assert_payload_contract(payload_a)
    _assert_payload_contract(payload_b)
    assert isinstance(payload_a["last_updated"], str) and payload_a["last_updated"]
    assert isinstance(payload_b["last_updated"], str) and payload_b["last_updated"]

    assert len(payload_a["panels"]) == len(payload_b["panels"])

    for panel_a, panel_b in zip(payload_a["panels"], payload_b["panels"]):
        assert isinstance(panel_a["last_updated"], str) and panel_a["last_updated"]
        assert isinstance(panel_b["last_updated"], str) and panel_b["last_updated"]
        assert _compute_metric_map(panel_a) == _compute_metric_map(panel_b)


def test_swing_compute_outputs_are_deterministic_between_calls():
    payload_a = get_swing()
    payload_b = get_swing()

    _assert_payload_contract(payload_a)
    _assert_payload_contract(payload_b)
    assert isinstance(payload_a["last_updated"], str) and payload_a["last_updated"]
    assert isinstance(payload_b["last_updated"], str) and payload_b["last_updated"]

    assert len(payload_a["panels"]) == len(payload_b["panels"])

    for panel_a, panel_b in zip(payload_a["panels"], payload_b["panels"]):
        assert isinstance(panel_a["last_updated"], str) and panel_a["last_updated"]
        assert isinstance(panel_b["last_updated"], str) and panel_b["last_updated"]
        assert _compute_metric_map(panel_a) == _compute_metric_map(panel_b)


def test_summary_structure_counts_and_guardrails_for_both_endpoints():
    for payload in (get_intraday(), get_swing()):
        assert payload["summary"]
        assert isinstance(payload["summary"], list)

        lead = next((line for line in payload["summary"] if line.startswith("Lead:")), "")
        support = next((line for line in payload["summary"] if line.startswith("Support:")), "")
        assert lead
        assert support
        assert 3 <= len(payload["summary"]) <= 5

        for line in payload["summary"]:
            _assert_no_banned_phrases(line)

        assert isinstance(payload["conditional_sensitivity"], list)
        for line in payload["conditional_sensitivity"]:
            _assert_no_banned_phrases(line)
        if payload["conditional_sensitivity"]:
            assert contains_force_keyword(payload["conditional_sensitivity"])
