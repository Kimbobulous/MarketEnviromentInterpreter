"use client";

import { useMemo, useState } from "react";
import { normalizeList } from "../../lib/normalize";

function extractLead(lines) {
  if (!Array.isArray(lines)) {
    return null;
  }

  const leadLine = lines.find((line) => typeof line === "string" && line.startsWith("Lead:"));
  if (!leadLine) {
    return null;
  }

  const match = leadLine.match(/^Lead:\s*([a-z][a-z\s-]*)\s+is\s+/i);
  if (!match || !match[1]) {
    return null;
  }
  return match[1].trim();
}

function extractStrength(lines) {
  const full = Array.isArray(lines) ? lines.join(" ") : "";
  const match = full.match(/\((strong|moderate|mixed)\)/i);
  return match ? match[1].toLowerCase() : "mixed";
}

function titleCase(value) {
  return String(value || "")
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

function summaryByLabel(lines) {
  const labels = {
    lead: "",
    support: "",
    mixed: "",
    scope: "",
    diagnostics: "",
  };

  lines.forEach((line) => {
    if (line.startsWith("Lead:")) labels.lead = line;
    else if (line.startsWith("Support:")) labels.support = line;
    else if (line.startsWith("Mixed") || line.startsWith("Signal balance:")) labels.mixed = line;
    else if (line.startsWith("Scope:")) labels.scope = line;
    else if (line.startsWith("Diagnostics:")) labels.diagnostics = line;
  });

  return labels;
}

function hasMixedSignals(lines, strength, diagnostics) {
  if (strength === "mixed") {
    return true;
  }

  const text = Array.isArray(lines) ? lines.join(" ").toLowerCase() : "";
  if (text.includes("mixed signals") || text.includes("shared across multiple")) {
    return true;
  }

  const match = String(diagnostics || "").match(/Tensions=(\d+)/i);
  if (!match) {
    return false;
  }

  const tensions = Number(match[1]);
  return Number.isFinite(tensions) && tensions > 0;
}

export default function SystemInsight({ summaryItems, sensitivityItems, loading }) {
  const [showDiagnostics, setShowDiagnostics] = useState(false);
  const [showSensitivity, setShowSensitivity] = useState(false);

  const summary = normalizeList(summaryItems);
  const sensitivity = normalizeList(sensitivityItems);

  const dominantForce = useMemo(() => extractLead(summary), [summary]);
  const strength = useMemo(() => extractStrength(summary), [summary]);
  const labeled = useMemo(() => summaryByLabel(summary), [summary]);
  const mixedSignals = useMemo(
    () => hasMixedSignals(summary, strength, labeled.diagnostics),
    [labeled.diagnostics, strength, summary]
  );

  if (loading) {
    return (
      <section className="system-insight">
        <h2>System Insight</h2>
        <div className="skeleton skeleton-title" />
        <div className="skeleton quant-skeleton-chart" />
        <div className="skeleton skeleton-list" />
        <div className="skeleton skeleton-list short" />
      </section>
    );
  }

  return (
    <section className="system-insight">
      <h2>System Insight</h2>

      <div className="insight-lead-row">
        <div>
          <p className="muted insight-label">Dominant Force</p>
          <span className="pill insight-force-pill">{dominantForce ? titleCase(dominantForce) : "Unavailable"}</span>
        </div>
        <div>
          <p className="muted insight-label">Strength</p>
          <span className={`pill insight-strength-pill strength-${strength}`}>{strength}</span>
        </div>
      </div>

      {mixedSignals && <p className="insight-mixed">Mixed-signal state active: review support and diagnostics jointly.</p>}

      <div className="divider" />

      <div className="insight-summary-block">
        <h3>Summary</h3>
        {labeled.lead && <p>{labeled.lead}</p>}
        {labeled.support && <p>{labeled.support}</p>}
        {labeled.mixed && <p>{labeled.mixed}</p>}
        {labeled.scope && <p>{labeled.scope}</p>}
        {!labeled.lead && !labeled.support && !labeled.mixed && !labeled.scope && (
          <p className="empty-copy">No summary available</p>
        )}
      </div>

      <button type="button" className="ui-button" onClick={() => setShowDiagnostics((prev) => !prev)}>
        {showDiagnostics ? "Hide" : "Show"} Diagnostics
      </button>
      <div className={`accordion-wrap ${showDiagnostics ? "open" : ""}`}>
        {labeled.diagnostics ? <p className="insight-diagnostics">{labeled.diagnostics}</p> : <p className="empty-copy">No diagnostics available</p>}
      </div>

      <button type="button" className="ui-button" onClick={() => setShowSensitivity((prev) => !prev)}>
        {showSensitivity ? "Hide" : "Show"} Conditional Sensitivity
      </button>
      <div className={`accordion-wrap ${showSensitivity ? "open" : ""}`}>
        {sensitivity.length > 0 ? (
          <ul className="bullet-list compact">
            {sensitivity.map((line, index) => (
              <li key={index}>{line}</li>
            ))}
          </ul>
        ) : (
          <p className="empty-copy">No conditional sensitivity available</p>
        )}
      </div>
    </section>
  );
}
