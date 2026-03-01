import { useState } from "react";
import { asText, normalizeList } from "../../lib/normalize";

const styles = {
  card: {
    border: "1px solid #d0d0d0",
    borderRadius: "6px",
    padding: "12px",
    background: "#fafafa",
    minHeight: "220px",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: "8px",
    marginBottom: "10px",
  },
  title: {
    margin: 0,
    fontSize: "16px",
  },
  meta: {
    marginTop: "6px",
    fontSize: "12px",
    color: "#555",
  },
  badge: {
    border: "1px solid #333",
    borderRadius: "12px",
    padding: "2px 8px",
    fontSize: "12px",
    whiteSpace: "nowrap",
  },
  badgeError: {
    borderColor: "#b00020",
    color: "#b00020",
  },
  badgePartial: {
    borderColor: "#9a6700",
    color: "#9a6700",
  },
  body: {
    opacity: 1,
  },
  bodyDim: {
    opacity: 0.7,
  },
  section: {
    marginBottom: "10px",
  },
  sectionLabel: {
    margin: "0 0 6px 0",
    fontSize: "13px",
    fontWeight: 600,
  },
  list: {
    margin: 0,
    paddingLeft: "18px",
  },
  listItem: {
    marginBottom: "4px",
    fontSize: "13px",
  },
  noData: {
    margin: 0,
    color: "#777",
    fontSize: "13px",
  },
  toggleButton: {
    border: "1px solid #333",
    background: "#fff",
    padding: "6px 10px",
    cursor: "pointer",
    fontSize: "13px",
  },
  whyText: {
    margin: "8px 0 0 0",
    fontSize: "13px",
    color: "#222",
  },
};

function renderList(items) {
  if (!Array.isArray(items) || items.length === 0) {
    return <p style={styles.noData}>No data</p>;
  }

  return (
    <ul style={styles.list}>
      {items.map((item, index) => (
        <li key={index} style={styles.listItem}>
          {item}
        </li>
      ))}
    </ul>
  );
}

export default function PanelCard({ panel, fallbackTitle }) {
  const [showWhy, setShowWhy] = useState(false);

  const safePanel = panel && typeof panel === "object" ? panel : {};
  const titleText = asText(safePanel.title).trim();
  const fallbackText = asText(fallbackTitle).trim();
  const title = titleText || fallbackText || "Panel";
  const lastUpdated = asText(safePanel.last_updated).trim();

  const statusRaw = asText(safePanel.status).trim();
  const statusKey = statusRaw.toLowerCase();
  const statusLabel =
    statusKey === "error" ? "error" : statusKey === "partial" ? "partial" : statusRaw;
  const isErrorStatus = statusKey === "error";

  const rawMetrics = normalizeList(safePanel.raw_metrics);
  const context = normalizeList(safePanel.context);
  const interpretation = normalizeList(safePanel.interpretation);
  const whyItems = normalizeList(safePanel.why_toggle);
  const hasWhy = whyItems.length > 0;

  const badgeStyle = {
    ...styles.badge,
    ...(statusKey === "error" ? styles.badgeError : {}),
    ...(statusKey === "partial" ? styles.badgePartial : {}),
  };

  return (
    <article style={styles.card}>
      <header style={styles.header}>
        <div>
          <h3 style={styles.title}>{title}</h3>
          {lastUpdated && <p style={styles.meta}>Last updated: {lastUpdated}</p>}
        </div>
        {statusRaw && <span style={badgeStyle}>{statusLabel}</span>}
      </header>

      <div style={{ ...styles.body, ...(isErrorStatus ? styles.bodyDim : {}) }}>
        <section style={styles.section}>
          <p style={styles.sectionLabel}>A) Raw Metrics</p>
          {renderList(rawMetrics)}
        </section>

        <section style={styles.section}>
          <p style={styles.sectionLabel}>B) Context</p>
          {renderList(context)}
        </section>

        <section style={styles.section}>
          <p style={styles.sectionLabel}>C) Interpretation</p>
          {renderList(interpretation)}
        </section>

        {hasWhy && (
          <section>
            <button
              type="button"
              style={styles.toggleButton}
              onClick={() => setShowWhy((prev) => !prev)}
            >
              Why this matters
            </button>
            {showWhy &&
              (whyItems.length === 1 ? (
                <p style={styles.whyText}>{whyItems[0]}</p>
              ) : (
                <div style={{ marginTop: "8px" }}>{renderList(whyItems)}</div>
              ))}
          </section>
        )}
      </div>
    </article>
  );
}
