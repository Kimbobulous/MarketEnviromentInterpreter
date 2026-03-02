import math

import pytest

from backend.lib.compute import classify_regime, rolling_percentile, trend_slope


def test_rolling_percentile_excludes_current_and_uses_prior_lookback():
    series = [1.0, 2.0, 2.0, 2.0]
    percentile = rolling_percentile(series, lookback=3)
    # Excluding current => prior [1, 2, 2], current=2:
    # less=1, equal=2 => (1 + 0.5*2) / 3 = 2/3
    assert math.isclose(percentile, 66.6666666667, rel_tol=0, abs_tol=1e-9)

    # If current were incorrectly included in the reference set, this value would differ.
    include_current_midpoint = 100.0 * ((1 + 0.5 * 3) / 4.0)
    assert not math.isclose(percentile, include_current_midpoint, rel_tol=0, abs_tol=1e-9)


def test_rolling_percentile_interior_value_not_pinned_to_extremes():
    series = [10.0, 30.0, 20.0, 40.0, 25.0]
    percentile = rolling_percentile(series, lookback=4)
    assert percentile == 50.0
    assert 0.0 < percentile < 100.0


def test_rolling_percentile_handles_ties_with_midpoint_rank():
    series = [1.0, 2.0, 2.0, 2.0, 4.0, 2.0]
    percentile = rolling_percentile(series, lookback=5)
    # prior [1,2,2,2,4], current=2 => less=1, equal=3 => (1 + 1.5) / 5 = 0.5
    assert percentile == 50.0


def test_rolling_percentile_returns_none_when_history_is_insufficient():
    assert rolling_percentile([1.0, 2.0], lookback=2) is None


def test_rolling_percentile_requires_positive_lookback():
    with pytest.raises(ValueError, match="positive integer"):
        rolling_percentile([1.0, 2.0, 3.0], lookback=0)


def test_classify_regime_boundaries():
    assert classify_regime(29.99) == "Low"
    assert classify_regime(30.0) == "Mid"
    assert classify_regime(70.0) == "Mid"
    assert classify_regime(70.01) == "High"


def test_trend_slope_positive_for_increasing_series():
    slope = trend_slope([1.0, 2.0, 4.0, 8.0])
    assert slope > 0


def test_trend_slope_negative_for_decreasing_series():
    slope = trend_slope([8.0, 4.0, 2.0, 1.0])
    assert slope < 0


def test_trend_slope_raises_for_non_positive_values():
    with pytest.raises(ValueError, match="strictly positive"):
        trend_slope([1.0, 0.0, 2.0])


def test_trend_slope_raises_for_too_short_series():
    with pytest.raises(ValueError, match="at least two"):
        trend_slope([1.0])


def test_trend_slope_flat_for_constant_series():
    slope = trend_slope([5.0, 5.0, 5.0, 5.0])
    assert math.isclose(slope, 0.0, abs_tol=1e-12)
