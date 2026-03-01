"use client";

import { useEffect, useState } from "react";
import MeiTabs from "../components/mei/MeiTabs";
import PanelCard from "../components/mei/PanelCard";
import SensitivitySection from "../components/mei/SensitivitySection";
import SummarySection from "../components/mei/SummarySection";

const PANEL_COUNTS = {
  intraday: 4,
  swing: 5,
};

const PANEL_LAYOUTS = {
  intraday: [2, 2],
  swing: [3, 2],
};

const styles = {
  page: {
    fontFamily: "Arial, sans-serif",
    padding: "16px",
    maxWidth: "1100px",
    margin: "0 auto",
  },
  heading: {
    margin: "0 0 12px 0",
  },
  statusRow: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    marginBottom: "16px",
  },
  error: {
    color: "#b00020",
    marginBottom: "12px",
  },
  retryButton: {
    border: "1px solid #333",
    background: "#fff",
    padding: "6px 10px",
    cursor: "pointer",
  },
  row: {
    display: "grid",
    gap: "12px",
    marginBottom: "12px",
  },
  placeholder: {
    border: "1px solid #d0d0d0",
    borderRadius: "6px",
    padding: "12px",
    background: "#f6f6f6",
    minHeight: "220px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  placeholderText: {
    margin: 0,
    fontSize: "14px",
    color: "#666",
  },
};

function buildPanelSlots(panels, tab) {
  const limit = PANEL_COUNTS[tab];
  const safePanels = Array.isArray(panels) ? panels.slice(0, limit) : [];
  const slots = [];

  for (let i = 0; i < limit; i += 1) {
    slots.push(i < safePanels.length ? safePanels[i] : null);
  }

  return slots;
}

function MissingPanelBox() {
  return (
    <article style={styles.placeholder}>
      <p style={styles.placeholderText}>Missing panel</p>
    </article>
  );
}

function PanelLayout({ tab, panels }) {
  const rows = PANEL_LAYOUTS[tab];
  const slots = buildPanelSlots(panels, tab);
  let cursor = 0;

  return (
    <section>
      {rows.map((columns, rowIndex) => {
        const rowStart = cursor;
        const rowPanels = slots.slice(rowStart, rowStart + columns);
        cursor += columns;

        return (
          <div
            key={`${tab}-row-${rowIndex}`}
            style={{ ...styles.row, gridTemplateColumns: `repeat(${columns}, 1fr)` }}
          >
            {rowPanels.map((panel, panelIndex) => {
              const absoluteIndex = rowStart + panelIndex;
              if (panel === null) {
                return (
                  <MissingPanelBox key={`${tab}-panel-${rowIndex}-${panelIndex}-missing`} />
                );
              }

              return (
                <PanelCard
                  key={`${tab}-panel-${rowIndex}-${panelIndex}`}
                  panel={panel}
                  fallbackTitle={`Panel ${absoluteIndex + 1}`}
                />
              );
            })}
          </div>
        );
      })}
    </section>
  );
}

export default function HomePage() {
  const [activeTab, setActiveTab] = useState("intraday");
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function fetchPayload(tab) {
    const endpoint = tab === "intraday" ? "/api/intraday" : "/api/swing";

    try {
      setLoading(true);
      setError(null);
      setPayload(null);

      const response = await fetch(endpoint);
      if (!response.ok) {
        setError(`Request failed with status ${response.status}`);
        return;
      }

      const json = await response.json();
      setPayload(json && typeof json === "object" ? json : {});
    } catch {
      setError("Unable to reach backend. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchPayload(activeTab);
  }, [activeTab]);

  return (
    <main style={styles.page}>
      <h1 style={styles.heading}>Market Environment Interpreter</h1>
      <MeiTabs activeTab={activeTab} onChange={setActiveTab} />

      <div style={styles.statusRow}>
        <span>Fetching: {activeTab === "intraday" ? "/api/intraday" : "/api/swing"}</span>
      </div>

      {loading && <p>Loading dashboard...</p>}
      {error && (
        <div style={styles.error}>
          <p>{error}</p>
          <button
            type="button"
            style={styles.retryButton}
            onClick={() => fetchPayload(activeTab)}
          >
            Retry
          </button>
        </div>
      )}

      {!loading && !error && (
        <>
          <PanelLayout
            tab={activeTab}
            panels={payload && Array.isArray(payload.panels) ? payload.panels : []}
          />
          {payload !== null && (
            <>
              <SensitivitySection items={payload.conditional_sensitivity} />
              <SummarySection items={payload.summary} />
            </>
          )}
        </>
      )}
    </main>
  );
}
