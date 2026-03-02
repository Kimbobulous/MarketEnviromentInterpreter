import SparklineTV from "../charts/SparklineTV";

function metricMap(rawMetrics) {
  const map = {};
  if (!Array.isArray(rawMetrics)) {
    return map;
  }

  rawMetrics.forEach((metric) => {
    if (!metric || typeof metric !== "object") {
      return;
    }
    const key = String(metric.key || "").trim();
    if (!key) {
      return;
    }
    map[key] = metric.value;
  });

  return map;
}

function formatMetricLabel(key) {
  return String(key || "")
    .replace(/_/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function panelKind(panelId) {
  const id = String(panelId || "").toLowerCase();
  if (id.includes("yield")) return "yield";
  if (id.includes("vix")) return "vix";
  if (id.startsWith("swing_")) return "ratio";
  return "generic";
}

function seriesDefinition(panelId) {
  const id = String(panelId || "").toLowerCase();
  if (id.includes("intraday_spy_state")) return "SPY close (daily)";
  if (id.includes("intraday_vix_state")) return "VIX index level";
  if (id.includes("intraday_yield_state")) return "10Y yield (DGS10, %)";
  if (id.includes("swing_breadth_participation")) return "Ratio: RSP/SPY";
  if (id.includes("swing_concentration_tilt")) return "Ratio: QQQ/SPY";
  if (id.includes("swing_risk_sentiment")) return "Ratio: HYG/SHY";
  if (id.includes("swing_vol_term_structure")) return "Ratio: VXX/VIX";
  return "Computed panel series";
}

function formatMetricValue(value, panelId, metricKey) {
  if (value === null || value === undefined || value === "") {
    return "N/A";
  }

  if (typeof value === "string") {
    return value;
  }

  if (typeof value === "number") {
    const kind = panelKind(panelId);
    const metric = String(metricKey || "").toLowerCase();

    if (kind === "yield" && (metric === "latest_value" || metric === "latest")) {
      return `${value.toFixed(2)}%`;
    }
    if (kind === "vix" && (metric === "latest_value" || metric === "latest")) {
      return value.toFixed(2);
    }
    if (kind === "ratio" && (metric === "latest_value" || metric === "latest")) {
      return value.toFixed(4);
    }
    if (metric === "trend_slope") {
      return value.toFixed(4);
    }

    if (Math.abs(value) >= 100) {
      return value.toFixed(1);
    }
    if (Math.abs(value) >= 10) {
      return value.toFixed(2);
    }
    return value.toFixed(3);
  }
  return String(value);
}

function getTrend(regime, trend) {
  const safeTrend = String(trend || "Unknown");
  return safeTrend;
}

function regimeClass(value) {
  const key = String(value || "").toLowerCase();
  if (key === "high") return "high";
  if (key === "low") return "low";
  return "mid";
}

function trendClass(value) {
  const key = String(value || "").toLowerCase();
  if (key === "up") return "up";
  if (key === "down") return "down";
  return "flat";
}

function chartColorFromTrend(trend) {
  const key = String(trend || "").toLowerCase();
  if (key === "up") return "#29cc7a";
  if (key === "down") return "#ff5d6c";
  return "#5aa8ff";
}

export default function ChartTile({ panel, index, tab, isFocused = false, onSelect }) {
  const safePanel = panel && typeof panel === "object" ? panel : {};
  const panelId = String(safePanel.id || "");
  const title = String(safePanel.title || `Panel ${index + 1}`);
  const status = String(safePanel.status || "unknown").toLowerCase();
  const metrics = metricMap(safePanel.raw_metrics);

  const regime = metrics.regime || "Unknown";
  const trend = metrics.trend_direction || "Unknown";
  const percentile =
    typeof metrics.percentile_lookback === "number" && Number.isFinite(metrics.percentile_lookback)
      ? Math.max(0, Math.min(100, metrics.percentile_lookback))
      : null;

  const highlights = [];
  ["latest_value", "latest", "trend_slope", "source_tickers"].forEach((key) => {
    if (Object.prototype.hasOwnProperty.call(metrics, key) && highlights.length < 3) {
      highlights.push({ key, value: metrics[key] });
    }
  });

  const badgeClass =
    status === "ok"
      ? "badge badge-ok"
      : status === "partial"
        ? "badge badge-partial"
        : "badge badge-error";

  const isPrimary = tab === "intraday" && String(safePanel.id || "").includes("spy");
  const canSelect = typeof onSelect === "function" && panelId;

  return (
    <article
      className={`quant-tile chart-tile surface ${isPrimary ? "is-primary" : ""} ${isFocused ? "is-focused" : ""} ${canSelect ? "is-selectable" : ""}`}
      role={canSelect ? "button" : undefined}
      tabIndex={canSelect ? 0 : undefined}
      onClick={canSelect ? () => onSelect(panelId) : undefined}
      onKeyDown={
        canSelect
          ? (event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSelect(panelId);
              }
            }
          : undefined
      }
      aria-pressed={canSelect ? isFocused : undefined}
    >
      <header className="chart-tile-head">
        <h3>{title}</h3>
        <span className={badgeClass}>{status}</span>
      </header>

      <div className="chart-tile-overlays">
        <span className={`pill tile-pill-regime regime-${regimeClass(regime)}`}>Regime: {regime}</span>
        <span className={`pill tile-pill-trend trend-${trendClass(trend)}`}>Trend: {getTrend(regime, trend)}</span>
      </div>

      <p className="tile-series-def muted">{seriesDefinition(panelId)}</p>

      <div className="chart-tile-plot">
        <SparklineTV
          data={safePanel.sparkline}
          times={safePanel.sparkline_times}
          height={isPrimary ? 120 : 84}
          color={chartColorFromTrend(trend)}
        />
      </div>

      {percentile !== null && (
        <div className="tile-percentile">
          <span>Pctl</span>
          <div className="tile-percentile-track">
            <div className="tile-percentile-fill" style={{ width: `${percentile}%` }} />
          </div>
          <strong>{percentile.toFixed(0)}</strong>
        </div>
      )}

      <div className="tile-highlights">
        {highlights.length > 0 ? (
          highlights.map((item) => (
            <div className="tile-metric" key={item.key}>
              <span>{formatMetricLabel(item.key)}</span>
              <strong>{formatMetricValue(item.value, panelId, item.key)}</strong>
            </div>
          ))
        ) : (
          <p className="empty-copy">No metric highlights</p>
        )}
      </div>
    </article>
  );
}
