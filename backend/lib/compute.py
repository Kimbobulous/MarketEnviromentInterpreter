"""Deterministic compute utilities for market state classification."""

import math


def rolling_percentile(series, lookback):
    """Return percentile rank (0-100) of last value vs prior lookback values.

    This implementation excludes the current value from the comparison set and
    uses the most recent ``lookback`` prior values. Percentile is computed as:

    ``100 * count(prior_value <= current_value) / lookback``

    Args:
        series: Ordered numeric values.
        lookback: Number of prior values to compare against.

    Returns:
        float percentile rank in the inclusive range [0, 100].

    Raises:
        ValueError: If lookback is invalid or the series is too short.
    """

    if lookback <= 0:
        raise ValueError("lookback must be a positive integer")
    if len(series) < lookback + 1:
        raise ValueError("series length must be at least lookback + 1")

    current = series[-1]
    prior = series[-(lookback + 1) : -1]
    less_or_equal = sum(1 for value in prior if value <= current)
    return 100.0 * less_or_equal / float(lookback)


def classify_regime(p):
    """Classify a percentile value into Low, Mid, or High regime."""

    if p < 30:
        return "Low"
    if p <= 70:
        return "Mid"
    return "High"


def trend_slope(series):
    """Return linear-regression slope on log(series) over full series.

    The x-axis is index position ``0..n-1`` and y is ``log(series[i])``.

    Args:
        series: Ordered numeric values.

    Returns:
        float slope of the best-fit line.

    Raises:
        ValueError: If fewer than two observations are provided or if any value
            is non-positive (log undefined).
    """

    n = len(series)
    if n < 2:
        raise ValueError("series must contain at least two values")
    if any(value <= 0 for value in series):
        raise ValueError("series values must be strictly positive for log slope")

    y_vals = [math.log(value) for value in series]
    x_vals = list(range(n))

    x_mean = sum(x_vals) / n
    y_mean = sum(y_vals) / n

    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, y_vals))
    denominator = sum((x - x_mean) ** 2 for x in x_vals)

    if denominator == 0:
        raise ValueError("cannot compute slope with zero x variance")

    return float(numerator / denominator)
