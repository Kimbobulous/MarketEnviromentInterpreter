import math

import pytest

from backend.lib.compute import classify_regime, rolling_percentile, trend_slope


def test_rolling_percentile_excludes_current_and_uses_prior_lookback():
    series = [10, 20, 30, 40]
    percentile = rolling_percentile(series, lookback=3)
    assert percentile == 100.0


def test_rolling_percentile_handles_ties_deterministically():
    series = [1.0, 2.0, 2.0]
    percentile = rolling_percentile(series, lookback=2)
    assert percentile == 100.0


def test_rolling_percentile_requires_sufficient_series_length():
    with pytest.raises(ValueError, match="lookback \\+ 1"):
        rolling_percentile([1.0, 2.0], lookback=2)


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
