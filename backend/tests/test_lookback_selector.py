import pytest
from fastapi import HTTPException

from backend import main


def test_intraday_default_behavior_unchanged_without_lookback():
    payload = main.get_intraday()

    assert "window_meta" not in payload
    for panel in payload.get("panels", []):
        window_meta = panel.get("window_meta", {})
        assert "lookback_selected" not in window_meta


@pytest.mark.parametrize("lookback", [20, 60, 252])
def test_intraday_lookback_selector_adds_payload_and_panel_window_meta(lookback):
    payload = main.get_intraday(lookback=lookback)

    assert payload["window_meta"]["lookback_selected"] == lookback
    assert payload["tab"] == "intraday"

    for panel in payload.get("panels", []):
        window_meta = panel.get("window_meta", {})
        assert window_meta.get("lookback_selected") == lookback
        assert window_meta.get("pctl_lookback") == lookback
        assert window_meta.get("trend_lookback") == lookback


@pytest.mark.parametrize("lookback", [20, 60, 252])
def test_swing_lookback_selector_adds_payload_and_panel_window_meta(lookback):
    payload = main.get_swing(lookback=lookback)

    assert payload["window_meta"]["lookback_selected"] == lookback
    assert payload["tab"] == "swing"

    for panel in payload.get("panels", []):
        window_meta = panel.get("window_meta", {})
        assert window_meta.get("lookback_selected") == lookback
        assert window_meta.get("pctl_lookback") == lookback
        assert window_meta.get("trend_lookback") == lookback


@pytest.mark.parametrize("bad_lookback", [None, 21, 0, -1, 999])
def test_invalid_lookback_rejected_with_clear_message(bad_lookback):
    if bad_lookback is None:
        # None is valid for default behavior and should not raise.
        payload = main.get_intraday(lookback=bad_lookback)
        assert payload["tab"] == "intraday"
        return

    with pytest.raises(HTTPException) as exc:
        main.get_intraday(lookback=bad_lookback)
    assert exc.value.status_code == 400
    assert "Allowed values are: 20, 60, 252" in str(exc.value.detail)
