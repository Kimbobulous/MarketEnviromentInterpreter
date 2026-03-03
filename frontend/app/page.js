"use client";

import { useCallback, useEffect, useState } from "react";
import MeiTabs from "../components/mei/MeiTabs";
import SeriesChartTV from "../components/charts/SeriesChartTV";
import ChartGrid from "../components/mei/ChartGrid";
import SystemInsight from "../components/mei/SystemInsight";
import InfoPill from "../components/ui/InfoPill";
import { getHelpText } from "../components/ui/helpText";
import { normalizeList } from "../lib/normalize";

const LOOKBACK_OPTIONS = [20, 60, 252];

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

function toNumberList(values) {
  if (!Array.isArray(values)) {
    return [];
  }
  return values.filter((value) => typeof value === "number" && Number.isFinite(value));
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

function extractLead(lines) {
  if (!Array.isArray(lines)) {
    return null;
  }
  const leadLine = lines.find((line) => typeof line === "string" && line.startsWith("Lead:"));
  if (!leadLine) {
    return null;
  }
  const match = leadLine.match(/^Lead:\s*([a-z][a-z\s-]*)\s+is\s+/i);
  return match && match[1] ? match[1].trim() : null;
}

function extractStrength(lines) {
  const full = Array.isArray(lines) ? lines.join(" ") : "";
  const match = full.match(/\((strong|moderate|mixed)\)/i);
  return match ? match[1].toLowerCase() : "mixed";
}

function hasMixedSignals(lines, strengthValue, diagnosticsLine) {
  if (strengthValue === "mixed") {
    return true;
  }
  const text = Array.isArray(lines) ? lines.join(" ").toLowerCase() : "";
  if (text.includes("mixed signals") || text.includes("shared across multiple")) {
    return true;
  }
  const match = String(diagnosticsLine || "").match(/Tensions=(\d+)/i);
  if (!match) {
    return false;
  }
  const tensions = Number(match[1]);
  return Number.isFinite(tensions) && tensions > 0;
}

function helpKeyForPanel(panel) {
  const id = String(panel?.id || "").toLowerCase();
  const title = String(panel?.title || "").toLowerCase();
  const haystack = `${id} ${title}`;
  if (haystack.includes("volatility term")) return "volatility_term_structure_proxy";
  if (haystack.includes("vxx") || haystack.includes("volatility")) return "volatility_proxy_vxx";
  if (haystack.includes("dgs10") || haystack.includes("yield") || haystack.includes("10y")) return "ten_year_yield_dgs10";
  if (haystack.includes("rsp/spy") || haystack.includes("breadth")) return "breadth_participation";
  if (haystack.includes("qqq/spy") || haystack.includes("concentration")) return "concentration_tilt";
  if (haystack.includes("hyg/shy") || haystack.includes("risk")) return "risk_sentiment";
  if (haystack.includes("spy")) return "spy_state";
  return "percentile";
}

function panelPresentation(panel, tab) {
  const id = String(panel?.id || "").toLowerCase();
  if (tab === "intraday" && id === "intraday_spy_state") {
    return {
      title: "SPY Price (Daily Close)",
      helpKey: "spy_state",
      microcopy:
        "Shows SPY's daily closing price over the selected lookback. Badges summarize how the latest reading compares to recent history (percentile/regime) and the window slope (trend).",
    };
  }
  if (tab === "intraday" && id === "intraday_vix_state") {
    return {
      title: "Volatility Proxy (VXX)",
      helpKey: "volatility_proxy_vxx",
      microcopy:
        "Tracks a VIX-linked ETF used as a proxy for volatility conditions; it is not the VIX index.",
    };
  }
  if (tab === "intraday" && id === "intraday_yield_state") {
    return {
      title: "10Y Treasury Yield (DGS10)",
      helpKey: "ten_year_yield_dgs10",
      microcopy:
        "Shows the 10-year yield level from FRED; badges summarize relative position and trend over the lookback.",
    };
  }
  return {
    title: String(panel?.title || "Panel"),
    helpKey: helpKeyForPanel(panel),
    microcopy: "Detailed view of the selected series over the active lookback window.",
  };
}

function HelpLabel({ label, helpKey }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center" }}>
      {label}
      <InfoPill text={getHelpText(helpKey)} label={`${label} help`} />
    </span>
  );
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
  const [selectedLookback, setSelectedLookback] = useState(60);
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
  const [hoverReadoutByTab, setHoverReadoutByTab] = useState({
    intraday: null,
    swing: null,
  });

  async function fetchPayload(tab, lookback) {
    const baseEndpoint = tab === "intraday" ? "/api/intraday" : "/api/swing";
    const query = new URLSearchParams({
      lookback: String(lookback),
    });
    const endpoint = `${baseEndpoint}?${query.toString()}`;

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
    fetchPayload(activeTab, selectedLookback);
  }, [activeTab, selectedLookback]);

  useEffect(() => {
    setRailOpen(false);
  }, [activeTab]);

  useEffect(() => {
    setHoverReadoutByTab((prev) => ({
      ...prev,
      [activeTab]: null,
    }));
  }, [activeTab, focusedByTab[activeTab]]);

  const panels = payload && Array.isArray(payload.panels) ? payload.panels : [];
  const displayPanels = panels.map((panel) => {
    const presentation = panelPresentation(panel, activeTab);
    return {
      ...panel,
      title: presentation.title,
      _presentation: presentation,
    };
  });

  useEffect(() => {
    const nextDefault = getDefaultFocusedId(activeTab, displayPanels);
    setFocusedByTab((prev) => {
      const current = prev[activeTab];
      const exists = displayPanels.some((panel) => panel?.id === current);
      if (exists) {
        return prev;
      }
      return {
        ...prev,
        [activeTab]: nextDefault,
      };
    });
  }, [activeTab, displayPanels]);

  const summary = normalizeList(payload?.summary);
  const sensitivity = normalizeList(payload?.conditional_sensitivity);
  const focusedPanelId = focusedByTab[activeTab];
  const focusedPanel = displayPanels.find((panel) => panel?.id === focusedPanelId) || displayPanels[0] || null;
  const focusedMetrics = metricMap(focusedPanel?.raw_metrics);
  const focusedValues = toNumberList(focusedPanel?.sparkline);

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
  const focusedTrendSlope =
    typeof focusedMetrics.trend_slope === "number" && Number.isFinite(focusedMetrics.trend_slope)
      ? focusedMetrics.trend_slope
      : typeof focusedMetrics.slope === "number" && Number.isFinite(focusedMetrics.slope)
        ? focusedMetrics.slope
        : null;
  const focusedFirst = focusedValues.length > 0 ? focusedValues[0] : null;
  const focusedLatest = focusedValues.length > 0 ? focusedValues[focusedValues.length - 1] : null;
  const focusedWindowLow = focusedValues.length > 0 ? Math.min(...focusedValues) : null;
  const focusedWindowHigh = focusedValues.length > 0 ? Math.max(...focusedValues) : null;
  const focusedChange =
    typeof focusedFirst === "number" && typeof focusedLatest === "number" ? focusedLatest - focusedFirst : null;
  const focusedChangePct =
    typeof focusedFirst === "number" && focusedFirst !== 0 && typeof focusedLatest === "number"
      ? ((focusedLatest - focusedFirst) / Math.abs(focusedFirst)) * 100
      : null;
  const focusedIsSpyPanel = String(focusedPanel?.id || "").toLowerCase().includes("spy");
  const focusedPanelHelpKey = focusedPanel?._presentation?.helpKey || helpKeyForPanel(focusedPanel);
  const focusedPanelTitle = focusedPanel?._presentation?.title || String(focusedPanel?.title || "Panel");
  const focusedPanelMicrocopy =
    focusedPanel?._presentation?.microcopy || "Detailed view of the selected series over the active lookback window.";
  const keyStatsRows = [
    { label: "Latest", helpKey: "latest", value: formatNumber(focusedLatest, 4) },
    { label: "Window Low", helpKey: "window_low", value: formatNumber(focusedWindowLow, 4) },
    { label: "Window High", helpKey: "window_high", value: formatNumber(focusedWindowHigh, 4) },
    { label: "Change", helpKey: "change_pct", value: formatNumber(focusedChange, 4) },
    { label: "Change %", helpKey: "change_pct", value: formatPercent(focusedChangePct, 2) },
    { label: "Window Length", helpKey: "window_length", value: String(focusedValues.length || 0) },
    {
      label: "Percentile",
      helpKey: "percentile",
      value:
        typeof focusedPercentile === "number" && Number.isFinite(focusedPercentile)
          ? focusedPercentile.toFixed(2)
          : "N/A",
    },
    { label: "Regime", helpKey: "regime", value: String(focusedRegime || "N/A") },
    { label: "Trend", helpKey: "trend", value: String(focusedTrend || "N/A") },
    {
      label: "Trend slope",
      helpKey: "trend_slope",
      value:
        typeof focusedTrendSlope === "number" && Number.isFinite(focusedTrendSlope)
          ? focusedTrendSlope.toFixed(6)
          : "N/A",
    },
  ];
  if (focusedIsSpyPanel) {
    keyStatsRows.push({
      label: "SPY state",
      helpKey: "spy_state",
      value: `${focusedRegime} / ${focusedTrend}`,
    });
  }
  const diagnosticsLine =
    summary.find((line) => typeof line === "string" && line.startsWith("Diagnostics:")) || "";
  const dominantForce = extractLead(summary) || "Unavailable";
  const strength = extractStrength(summary);
  const mixedSignals = hasMixedSignals(summary, strength, diagnosticsLine);

  const selectFocusedPanel = (panelId) => {
    setFocusedByTab((prev) => ({
      ...prev,
      [activeTab]: panelId,
    }));
  };
  const handleFocusedHover = useCallback(
    (hoverValue) => {
      setHoverReadoutByTab((prev) => {
        const current = prev[activeTab];
        const isSame =
          (current === null && hoverValue === null) ||
          (current &&
            hoverValue &&
            current.dateLabel === hoverValue.dateLabel &&
            current.valueLabel === hoverValue.valueLabel &&
            current.deltaText === hoverValue.deltaText);
        if (isSame) {
          return prev;
        }
        return {
          ...prev,
          [activeTab]: hoverValue,
        };
      });
    },
    [activeTab]
  );
  const focusedView = focusedViewByTab[activeTab] || "summary";
  const focusedHoverReadout = hoverReadoutByTab[activeTab];
  const effectiveLookback =
    typeof payload?.window_meta?.lookback_selected === "number"
      ? payload.window_meta.lookback_selected
      : selectedLookback;

  return (
    <main className="quant-app">
      <header className="quant-topbar surface">
        <div>
          <p className="quant-kicker">MEI Terminal</p>
          <h1>Market Environment Interpreter</h1>
          <p className="subtle-source">
            Data source: {activeTab === "intraday" ? "/api/intraday" : "/api/swing"} · Lookback: {effectiveLookback}
          </p>
        </div>
        <div className="quant-topbar-controls">
          <MeiTabs activeTab={activeTab} onChange={setActiveTab} />
          <div style={{ display: "flex", gap: "0.45rem", alignItems: "center", flexWrap: "wrap" }}>
            <span className="muted" style={{ display: "inline-flex", alignItems: "center", fontSize: "0.82rem" }}>
              Lookback
              <InfoPill text={getHelpText("lookback_window")} label="Lookback window help" />
            </span>
            <div style={{ display: "flex", gap: "0.35rem", alignItems: "center", flexWrap: "wrap" }}>
              {LOOKBACK_OPTIONS.map((option) => (
                <button
                  key={option}
                  type="button"
                  className={`ui-button ${selectedLookback === option ? "is-active" : ""}`}
                  onClick={() => setSelectedLookback(option)}
                  aria-pressed={selectedLookback === option}
                >
                  {option}
                </button>
              ))}
            </div>
            <span className="muted" style={{ fontSize: "0.78rem" }}>
              sessions
            </span>
          </div>
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
              <button type="button" className="ui-button" onClick={() => fetchPayload(activeTab, selectedLookback)}>
                Retry
              </button>
            </div>
          )}

          {!loading && !error && (
            <div key={activeTab} className="tab-switch-fade">
              {focusedPanel && (
                <section className="focused-chart surface">
                  <div className="focused-chart-head">
                    <div>
                      <h2 style={{ display: "inline-flex", alignItems: "center" }}>
                        {focusedPanelTitle}
                        <InfoPill text={getHelpText(focusedPanelHelpKey)} label={`${focusedPanelTitle} help`} />
                      </h2>
                      <p className="muted">Detailed view (hover to inspect values)</p>
                      <p className="muted" style={{ maxWidth: 760 }}>
                        {focusedPanelMicrocopy}
                      </p>
                      <p className="muted" style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
                        <span>
                          <HelpLabel label="Regime" helpKey="regime" />: {focusedRegime}
                        </span>
                        <span>
                          <HelpLabel label="Trend" helpKey="trend" />: {focusedTrend}
                        </span>
                        <span>
                          <HelpLabel label="Trend slope" helpKey="trend_slope" />:{" "}
                          {typeof focusedTrendSlope === "number" ? focusedTrendSlope.toFixed(6) : "N/A"}
                        </span>
                      </p>
                    </div>
                    {focusedHoverReadout && (
                      <div
                        style={{
                          border: "1px solid #355173",
                          borderRadius: 10,
                          background: "rgba(9, 16, 27, 0.95)",
                          color: "#deebfc",
                          padding: "0.38rem 0.55rem",
                          fontSize: "0.73rem",
                          lineHeight: 1.35,
                          minWidth: 170,
                          textAlign: "right",
                        }}
                        aria-live="polite"
                      >
                        <div>{focusedHoverReadout.dateLabel}</div>
                        <div>Value: {focusedHoverReadout.valueLabel}</div>
                        {focusedHoverReadout.deltaText && <div>Δ: {focusedHoverReadout.deltaText}</div>}
                      </div>
                    )}
                  </div>
                  <SeriesChartTV
                    data={focusedPanel.sparkline}
                    timeLabels={focusedPanel.sparkline_times}
                    height={320}
                    regime={focusedRegime}
                    trend={focusedTrend}
                    percentile={focusedPercentile}
                    showFloatingTooltip={false}
                    onHoverChange={handleFocusedHover}
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
                      <section className="key-stats-wrap">
                        <h3>Key Stats</h3>
                        <table className="key-stats-table" aria-label="Key Stats table">
                          <tbody>
                            {keyStatsRows.map((row) => (
                              <tr key={row.label}>
                                <th scope="row">
                                  <HelpLabel label={row.label} helpKey={row.helpKey} />
                                </th>
                                <td>{row.value}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </section>
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
                panels={displayPanels}
                focusedPanelId={focusedPanel?.id || null}
                onSelectPanel={selectFocusedPanel}
              />
            </div>
          )}
        </div>

        <aside className={`quant-right-rail surface ${railOpen ? "open" : ""}`}>
          <section
            style={{
              border: "1px solid rgba(62, 91, 122, 0.6)",
              borderRadius: 12,
              padding: "0.55rem 0.7rem",
              marginBottom: "0.7rem",
              background: "rgba(7, 15, 25, 0.35)",
            }}
          >
            <h3 style={{ marginBottom: "0.45rem" }}>Insight Labels</h3>
            <p className="muted" style={{ marginBottom: "0.25rem" }}>
              <HelpLabel label="Dominant Force" helpKey="dominant_force" />: {dominantForce}
            </p>
            <p className="muted" style={{ marginBottom: "0.25rem" }}>
              <HelpLabel label="Strength" helpKey="strength" />: {strength}
            </p>
            <p className="muted">
              <HelpLabel label="Mixed signals" helpKey="mixed_signals" />: {mixedSignals ? "Yes" : "No"}
            </p>
          </section>
          <SystemInsight summaryItems={summary} sensitivityItems={sensitivity} loading={loading} />
        </aside>
      </section>
    </main>
  );
}
