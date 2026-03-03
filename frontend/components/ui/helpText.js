export const HELP_TEXT = {
  percentile:
    "Percentile ranks the latest value against prior values in the selected lookback window (excluding the current bar).\nHigher values indicate the latest reading is nearer the top of its recent distribution.",
  regime:
    "Regime is a categorical state label derived from the indicator level and context rules.\nIt is a compact description of current conditions, not a forecast.",
  trend:
    "Trend describes recent directional drift (up, down, or flat) in the computed series over the active window.\nIt is descriptive context rather than a guarantee of future movement.",
  trend_slope:
    "Trend slope is the estimated rate of change across the trend window.\nA larger absolute slope means stronger recent directional drift in that window.",
  lookback_window:
    "Controls how far back we compare when computing percentiles and trend. Shorter windows react faster; longer windows smooth noise.",
  dominant_force:
    "Dominant Force is the primary driver surfaced by the weighting engine from Lead and Support evidence.\nIt summarizes what has the strongest combined influence in the current snapshot.",
  strength:
    "Strength describes confidence of the dominant force (for example strong, moderate, mixed) based on force separation and diagnostic tension.\nIt is used as a gauge for coherence across signals.",
  mixed_signals:
    "Mixed signals indicates meaningful disagreement across force groups.\nHistorically this is associated with less directional clarity and higher interpretation uncertainty.",
  spy_state:
    "SPY state summarizes broad large-cap U.S. equity conditions using SPY as a market proxy.\nUsed as a gauge for baseline equity backdrop in this dashboard.",
  volatility_proxy_vxx:
    "Volatility proxy (VXX) is an ETN-based proxy used when direct VIX index access is unavailable.\nIt is not the VIX index itself and should be interpreted as a proxy signal.",
  ten_year_yield_dgs10:
    "10Y yield (DGS10) is the U.S. 10-year Treasury constant maturity rate from FRED.\nUsed as a macro rate gauge for growth, discount-rate, and risk-context interpretation.",
  breadth_participation:
    "Breadth Participation (RSP/SPY) compares equal-weight S&P 500 exposure with cap-weight S&P 500.\nUsed as a gauge for whether participation is broad or concentrated.",
  concentration_tilt:
    "Concentration Tilt (QQQ/SPY) compares tech-heavy Nasdaq exposure versus broad S&P exposure.\nUsed as a gauge for mega-cap growth concentration versus broader market balance.",
  risk_sentiment:
    "Risk Sentiment (HYG/SHY) compares high-yield credit versus short Treasuries.\nHistorically associated with changing risk appetite in credit-sensitive conditions.",
  volatility_term_structure_proxy:
    "Volatility Term Structure Proxy uses VXX behavior as a practical proxy for volatility-curve stress when direct index term-structure access is limited.\nUsed as a gauge for relative stress versus normalization.",
  window_high:
    "Window High is the highest observed value inside the current analysis window.",
  window_low:
    "Window Low is the lowest observed value inside the current analysis window.",
  window_length:
    "Window Length is the number of data points currently included in the panel series window.",
  change_pct:
    "Change % is the percentage move from the first value in the window to the latest value.",
  latest:
    "Latest is the most recent available value in the panel series.",
};

export function getHelpText(key) {
  if (!key) {
    return "";
  }
  return HELP_TEXT[key] || "";
}
