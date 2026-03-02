"""Deterministic compute utilities for market state classification."""

import math


def rolling_percentile(series, lookback):
    """Return percentile rank (0-100) of last value vs prior lookback values.

    This implementation excludes the current value from the comparison set and
    uses the most recent ``lookback`` prior values.

    Tie handling uses midpoint rank among equals:

    ``100 * (count(prior_value < current_value) + 0.5 * count(prior_value == current_value)) / lookback``

    Args:
        series: Ordered numeric values.
        lookback: Number of prior values to compare against.

    Returns:
        float percentile rank in the inclusive range [0, 100], or ``None``
        when there is insufficient history (< lookback + 1).

    Raises:
        ValueError: If lookback is invalid.
    """

    if lookback <= 0:
        raise ValueError("lookback must be a positive integer")
    if len(series) < lookback + 1:
        return None

    current = series[-1]
    prior = series[-(lookback + 1) : -1]
    count_less = sum(1 for value in prior if value < current)
    count_equal = sum(1 for value in prior if value == current)
    midpoint_rank = count_less + (0.5 * count_equal)
    return 100.0 * midpoint_rank / float(lookback)


def rolling_percentile_series(series, lookback):
    """Return rolling percentiles for each point with enough history.

    Uses ``rolling_percentile`` for every eligible index and therefore
    preserves the existing "exclude current" behavior.
    """

    if lookback <= 0:
        raise ValueError("lookback must be a positive integer")

    out = []
    for idx in range(lookback, len(series)):
        value = rolling_percentile(series[: idx + 1], lookback=lookback)
        if value is None:
            continue
        out.append(float(value))
    return out


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
