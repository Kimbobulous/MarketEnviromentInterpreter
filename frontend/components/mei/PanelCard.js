import { useMemo, useState } from "react";
import { asText, normalizeList } from "../../lib/normalize";

function prettyLabel(value) {
  return String(value || "")
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatMetricValue(metric) {
  if (metric && typeof metric === "object") {
    const raw = metric.value;
    if (raw === null || raw === undefined || raw === "") {
      return "N/A";
    }

    if (typeof raw === "number") {
      const rounded = Math.abs(raw) >= 10 ? raw.toFixed(2) : raw.toFixed(4);
      const unit = asText(metric.unit).trim();
      return unit ? `${rounded} ${unit}` : rounded;
    }

    const text = asText(raw).trim();
    const unit = asText(metric.unit).trim();
    return unit && text ? `${text} ${unit}` : text || "N/A";
  }

  return asText(metric).trim() || "N/A";
}

function RawMetricRows({ rows }) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return <p className="empty-copy">No data</p>;
  }

  return (
    <div className="metric-grid" role="table" aria-label="Raw metrics">
      {rows.map((metric, index) => {
        const key = asText(metric?.key).trim() || `metric-${index + 1}`;
        return (
          <div className="metric-row" role="row" key={`${key}-${index}`}>
            <span className="metric-key" role="cell">
              {prettyLabel(key)}
            </span>
            <span className="metric-value" role="cell">
              {formatMetricValue(metric)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function BulletSection({ title, items }) {
  const list = normalizeList(items);
  return (
    <section className="panel-section">
      <h4 className="panel-section-title">{title}</h4>
      {list.length === 0 ? (
        <p className="empty-copy">No data</p>
      ) : (
        <ul className="bullet-list compact">
          {list.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function PanelCard({ panel, fallbackTitle }) {
  const [showWhy, setShowWhy] = useState(false);

  const safePanel = panel && typeof panel === "object" ? panel : {};
  const titleText = asText(safePanel.title).trim();
  const fallbackText = asText(fallbackTitle).trim();
  const title = titleText || fallbackText || "Panel";
  const lastUpdated = asText(safePanel.last_updated).trim();

  const statusRaw = asText(safePanel.status).trim() || "unknown";
  const statusKey = statusRaw.toLowerCase();
  const badgeClass =
    statusKey === "ok"
      ? "badge badge-ok"
      : statusKey === "partial"
        ? "badge badge-partial"
        : "badge badge-error";

  const rawMetrics = useMemo(
    () => (Array.isArray(safePanel.raw_metrics) ? safePanel.raw_metrics : []),
    [safePanel.raw_metrics]
  );

  const context = normalizeList(safePanel.context);
  const interpretation = normalizeList(safePanel.interpretation);
  const whyItems = normalizeList(safePanel.why_toggle);
  const hasWhy = whyItems.length > 0;

  return (
    <article className={`dashboard-card panel-card ${statusKey === "error" ? "is-error" : ""}`}>
      <header className="panel-header">
        <div>
          <h3 className="panel-title">{title}</h3>
          {lastUpdated && <p className="panel-meta">Last updated: {lastUpdated}</p>}
        </div>
        <span className={badgeClass}>{statusRaw}</span>
      </header>

      <section className="panel-section">
        <h4 className="panel-section-title">Raw Metrics</h4>
        <RawMetricRows rows={rawMetrics} />
      </section>

      <BulletSection title="Context" items={context} />
      <BulletSection title="Interpretation" items={interpretation} />

      {hasWhy && (
        <section className="panel-section">
          <button
            type="button"
            className="ui-button"
            aria-expanded={showWhy}
            onClick={() => setShowWhy((prev) => !prev)}
          >
            Why this matters
          </button>

          <div className={`accordion-wrap ${showWhy ? "open" : ""}`}>
            {whyItems.length === 1 ? (
              <p className="panel-copy">{whyItems[0]}</p>
            ) : (
              <ul className="bullet-list compact">
                {whyItems.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            )}
          </div>
        </section>
      )}
    </article>
  );
}
