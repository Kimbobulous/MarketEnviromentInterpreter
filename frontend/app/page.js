"use client";

import { useEffect, useState } from "react";
import MeiTabs from "../components/mei/MeiTabs";
import ChartTile from "../components/mei/ChartTile";
import SystemInsight from "../components/mei/SystemInsight";
import { normalizeList } from "../lib/normalize";

function formatTimestamp(value) {
  if (!value || typeof value !== "string") {
    return "Waiting for data";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function ChartGrid({ tab, panels }) {
  const safePanels = Array.isArray(panels) ? panels.filter(Boolean) : [];
  return (
    <section className={`quant-grid ${tab === "swing" ? "quant-grid-swing" : "quant-grid-intraday"}`}>
      {safePanels.map((panel, index) => (
        <ChartTile key={panel?.id || `${tab}-panel-${index}`} panel={panel} index={index} tab={tab} />
      ))}
    </section>
  );
}

function LoadingSkeleton({ tab }) {
  const count = tab === "swing" ? 4 : 3;
  return (
    <section className={`quant-grid ${tab === "swing" ? "quant-grid-swing" : "quant-grid-intraday"}`}>
      {Array.from({ length: count }).map((_, index) => (
        <article className="quant-tile surface" key={`${tab}-skeleton-${index}`}>
          <div className="skeleton skeleton-title" />
          <div className="skeleton skeleton-meta" />
          <div className="skeleton quant-skeleton-chart" />
          <div className="skeleton skeleton-list" />
          <div className="skeleton skeleton-list short" />
        </article>
      ))}
    </section>
  );
}

export default function HomePage() {
  const [activeTab, setActiveTab] = useState("intraday");
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [railOpen, setRailOpen] = useState(false);

  async function fetchPayload(tab) {
    const endpoint = tab === "intraday" ? "/api/intraday" : "/api/swing";

    try {
      setLoading(true);
      setError(null);

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

  useEffect(() => {
    setRailOpen(false);
  }, [activeTab]);

  const summary = normalizeList(payload?.summary);
  const sensitivity = normalizeList(payload?.conditional_sensitivity);

  return (
    <main className="quant-app">
      <header className="quant-topbar surface">
        <div>
          <p className="quant-kicker">MEI Terminal</p>
          <h1>Market Environment Interpreter</h1>
          <p className="subtle-source">Data source: {activeTab === "intraday" ? "/api/intraday" : "/api/swing"}</p>
        </div>
        <div className="quant-topbar-controls">
          <MeiTabs activeTab={activeTab} onChange={setActiveTab} />
          <p className="muted quant-updated">Updated: {formatTimestamp(payload?.last_updated)}</p>
          <button type="button" className="ui-button rail-toggle" onClick={() => setRailOpen((prev) => !prev)}>
            {railOpen ? "Hide Insight" : "Show Insight"}
          </button>
        </div>
      </header>

      <section className="quant-main-grid">
        <div className="quant-left-col">
          {loading && <LoadingSkeleton tab={activeTab} />}

          {error && (
            <div className="error-banner" role="alert">
              <p>{error}</p>
              <button type="button" className="ui-button" onClick={() => fetchPayload(activeTab)}>
                Retry
              </button>
            </div>
          )}

          {!loading && !error && (
            <div key={activeTab} className="tab-switch-fade">
              <ChartGrid tab={activeTab} panels={payload && Array.isArray(payload.panels) ? payload.panels : []} />
            </div>
          )}
        </div>

        <aside className={`quant-right-rail surface ${railOpen ? "open" : ""}`}>
          <SystemInsight summaryItems={summary} sensitivityItems={sensitivity} loading={loading} />
        </aside>
      </section>
    </main>
  );
}
