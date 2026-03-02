"use client";

import { useEffect, useState } from "react";
import MeiTabs from "../components/mei/MeiTabs";
import PanelCard from "../components/mei/PanelCard";
import SensitivitySection from "../components/mei/SensitivitySection";
import SummarySection from "../components/mei/SummarySection";

function PanelLayout({ tab, panels }) {
  const safePanels = Array.isArray(panels) ? panels : [];

  return (
    <section className={`panel-grid ${tab === "swing" ? "panel-grid-swing" : "panel-grid-intraday"}`}>
      {safePanels.map((panel, index) => (
        <PanelCard key={panel?.id || `${tab}-panel-${index}`} panel={panel} fallbackTitle={`Panel ${index + 1}`} />
      ))}
    </section>
  );
}

function LoadingSkeleton({ tab }) {
  const count = tab === "swing" ? 4 : 3;
  return (
    <section className={`panel-grid ${tab === "swing" ? "panel-grid-swing" : "panel-grid-intraday"}`}>
      {Array.from({ length: count }).map((_, index) => (
        <article className="dashboard-card panel-card" key={`${tab}-skeleton-${index}`}>
          <div className="skeleton skeleton-title" />
          <div className="skeleton skeleton-meta" />
          <div className="skeleton skeleton-row" />
          <div className="skeleton skeleton-row" />
          <div className="skeleton skeleton-row short" />
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
    <main className="dashboard-shell">
      <header className="dashboard-header">
        <h1>Market Environment Interpreter</h1>
        <p className="subtle-source">
          Data source: {activeTab === "intraday" ? "/api/intraday" : "/api/swing"}
        </p>
      </header>

      <MeiTabs activeTab={activeTab} onChange={setActiveTab} />

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
        <>
          <PanelLayout tab={activeTab} panels={payload && Array.isArray(payload.panels) ? payload.panels : []} />

          {payload !== null && (
            <section className="below-panels">
              <SensitivitySection items={payload.conditional_sensitivity} />
              <SummarySection items={payload.summary} />
            </section>
          )}
        </>
      )}
    </main>
  );
}
