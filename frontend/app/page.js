"use client";

import { useEffect, useState } from "react";
import MeiTabs from "../components/mei/MeiTabs";
import SeriesChartTV from "../components/charts/SeriesChartTV";
import ChartGrid from "../components/mei/ChartGrid";
import KeyStatsTable from "../components/mei/KeyStatsTable";
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

function metricMap(rawMetrics) {
  const map = {};
  if (!Array.isArray(rawMetrics)) {
    return map;
  }
  rawMetrics.forEach((metric) => {
    if (!metric || typeof metric !== "object" || !metric.key) {
      return;
    }
    map[String(metric.key)] = metric.value;
  });
  return map;
}

function getDefaultFocusedId(tab, panels) {
  const safePanels = Array.isArray(panels) ? panels.filter(Boolean) : [];
  if (safePanels.length === 0) {
    return null;
  }

  const preferred =
    tab === "intraday"
      ? safePanels.find((panel) => String(panel?.id || "").includes("spy"))
      : safePanels.find((panel) => String(panel?.id || "").includes("breadth"));
  return (preferred && preferred.id) || safePanels[0].id || null;
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
  const [focusedByTab, setFocusedByTab] = useState({
    intraday: null,
    swing: null,
  });
  const [focusedViewByTab, setFocusedViewByTab] = useState({
    intraday: "summary",
    swing: "summary",
  });

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

  const panels = payload && Array.isArray(payload.panels) ? payload.panels : [];

  useEffect(() => {
    const nextDefault = getDefaultFocusedId(activeTab, panels);
    setFocusedByTab((prev) => {
      const current = prev[activeTab];
      const exists = panels.some((panel) => panel?.id === current);
      if (exists) {
        return prev;
      }
      return {
        ...prev,
        [activeTab]: nextDefault,
      };
    });
  }, [activeTab, panels]);

  const summary = normalizeList(payload?.summary);
  const sensitivity = normalizeList(payload?.conditional_sensitivity);
  const focusedPanelId = focusedByTab[activeTab];
  const focusedPanel = panels.find((panel) => panel?.id === focusedPanelId) || panels[0] || null;
  const focusedMetrics = metricMap(focusedPanel?.raw_metrics);

  const focusedRegime =
    typeof focusedMetrics.regime === "string" && focusedMetrics.regime ? focusedMetrics.regime : "Unknown";
  const focusedTrend =
    typeof focusedMetrics.trend_direction === "string" && focusedMetrics.trend_direction
      ? focusedMetrics.trend_direction
      : "Unknown";
  const focusedPercentile =
    typeof focusedMetrics.percentile_lookback === "number" && Number.isFinite(focusedMetrics.percentile_lookback)
      ? focusedMetrics.percentile_lookback
      : null;

  const selectFocusedPanel = (panelId) => {
    setFocusedByTab((prev) => ({
      ...prev,
      [activeTab]: panelId,
    }));
  };
  const focusedView = focusedViewByTab[activeTab] || "summary";

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
              {focusedPanel && (
                <section className="focused-chart surface">
                  <div className="focused-chart-head">
                    <h2>{focusedPanel.title}</h2>
                    <p className="muted">Focused chart</p>
                  </div>
                  <SeriesChartTV
                    data={focusedPanel.sparkline}
                    timeLabels={focusedPanel.sparkline_times}
                    height={320}
                    regime={focusedRegime}
                    trend={focusedTrend}
                    percentile={focusedPercentile}
                  />

                  <div className="focused-subtabs">
                    <button
                      type="button"
                      className={`ui-button ${focusedView === "summary" ? "is-active" : ""}`}
                      onClick={() =>
                        setFocusedViewByTab((prev) => ({
                          ...prev,
                          [activeTab]: "summary",
                        }))
                      }
                    >
                      Summary
                    </button>
                    <button type="button" className="ui-button" disabled title="Coming soon">
                      News
                    </button>
                  </div>

                  {focusedView === "summary" && (
                    <div className="focused-summary-grid">
                      <KeyStatsTable panel={focusedPanel} />
                      <section className="focused-interpretation">
                        <h3>Interpretation</h3>
                        {normalizeList(focusedPanel.interpretation).length > 0 ? (
                          <ul className="bullet-list compact">
                            {normalizeList(focusedPanel.interpretation).map((line, index) => (
                              <li key={index}>{line}</li>
                            ))}
                          </ul>
                        ) : (
                          <p className="empty-copy">No interpretation available</p>
                        )}
                        <p className="muted news-note">News tab: Coming soon.</p>
                      </section>
                    </div>
                  )}
                </section>
              )}

              <ChartGrid
                tab={activeTab}
                panels={panels}
                focusedPanelId={focusedPanel?.id || null}
                onSelectPanel={selectFocusedPanel}
              />
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
