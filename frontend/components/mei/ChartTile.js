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

function formatMetricValue(value) {
  if (value === null || value === undefined || value === "") {
    return "N/A";
  }
  if (typeof value === "number") {
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
  const safeRegime = String(regime || "Unknown");
  const safeTrend = String(trend || "Unknown");
  return `${safeRegime} · ${safeTrend}`;
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

export default function ChartTile({ panel, index, tab }) {
  const safePanel = panel && typeof panel === "object" ? panel : {};
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

  return (
    <article className={`quant-tile chart-tile surface ${isPrimary ? "is-primary" : ""}`}>
      <header className="chart-tile-head">
        <h3>{title}</h3>
        <span className={badgeClass}>{status}</span>
      </header>

      <div className="chart-tile-overlays">
        <span className={`pill tile-pill-regime regime-${regimeClass(regime)}`}>{regime}</span>
        <span className={`pill tile-pill-trend trend-${trendClass(trend)}`}>{getTrend(regime, trend)}</span>
      </div>

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
              <strong>{formatMetricValue(item.value)}</strong>
            </div>
          ))
        ) : (
          <p className="empty-copy">No metric highlights</p>
        )}
      </div>
    </article>
  );
}
