function toNumberList(values) {
  if (!Array.isArray(values)) {
    return [];
  }
  return values.filter((value) => typeof value === "number" && Number.isFinite(value));
}

function metricMap(rawMetrics) {
  const out = {};
  if (!Array.isArray(rawMetrics)) {
    return out;
  }

  rawMetrics.forEach((metric) => {
    if (!metric || typeof metric !== "object") {
      return;
    }
    const key = String(metric.key || "").trim();
    if (!key) {
      return;
    }
    out[key] = metric.value;
  });

  return out;
}

function formatNumber(value, digits = 4) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "N/A";
  }
  return value.toFixed(digits);
}

function formatPercent(value, digits = 2) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "N/A";
  }
  return `${value.toFixed(digits)}%`;
}

export default function KeyStatsTable({ panel }) {
  const safePanel = panel && typeof panel === "object" ? panel : {};
  const values = toNumberList(safePanel.sparkline);
  const metrics = metricMap(safePanel.raw_metrics);

  const first = values.length > 0 ? values[0] : null;
  const latest = values.length > 0 ? values[values.length - 1] : null;
  const min = values.length > 0 ? Math.min(...values) : null;
  const max = values.length > 0 ? Math.max(...values) : null;
  const change =
    typeof first === "number" && typeof latest === "number" ? latest - first : null;
  const changePct =
    typeof first === "number" && first !== 0 && typeof latest === "number"
      ? ((latest - first) / Math.abs(first)) * 100
      : null;

  const rows = [
    { label: "Latest", value: formatNumber(latest, 4) },
    { label: "Window Low", value: formatNumber(min, 4) },
    { label: "Window High", value: formatNumber(max, 4) },
    { label: "Change", value: formatNumber(change, 4) },
    { label: "Change %", value: formatPercent(changePct, 2) },
    { label: "Window Length", value: String(values.length || 0) },
    {
      label: "Percentile",
      value:
        typeof metrics.percentile_lookback === "number"
          ? metrics.percentile_lookback.toFixed(2)
          : "N/A",
    },
    { label: "Regime", value: String(metrics.regime || "N/A") },
    { label: "Trend", value: String(metrics.trend_direction || "N/A") },
  ];

  return (
    <section className="key-stats-wrap">
      <h3>Key Stats</h3>
      <table className="key-stats-table" aria-label="Key Stats table">
        <tbody>
          {rows.map((row) => (
            <tr key={row.label}>
              <th scope="row">{row.label}</th>
              <td>{row.value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
