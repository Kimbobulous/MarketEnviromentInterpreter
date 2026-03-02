import { normalizeList } from "../../lib/normalize";

function extractDominantForce(lines) {
  if (!Array.isArray(lines)) {
    return null;
  }

  const leadLine = lines.find(
    (line) => typeof line === "string" && line.trim().startsWith("Lead:")
  );
  if (!leadLine) {
    return null;
  }

  const match = leadLine.match(/^Lead:\s*([a-z][a-z\s-]*)\s+is\s+/i);
  if (!match || !match[1]) {
    return null;
  }

  const force = match[1].trim();
  return force ? force : null;
}

function titleCase(value) {
  return String(value)
    .split(/[\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

export default function SummarySection({ items }) {
  const safeItems = normalizeList(items);
  const dominantForce = extractDominantForce(safeItems);

  return (
    <section className="dashboard-card section-card">
      <div className="section-header-row">
        <h2>Summary</h2>
        {dominantForce && (
          <span className="badge badge-ok">Dominant: {titleCase(dominantForce)}</span>
        )}
      </div>

      {safeItems.length === 0 && <p className="empty-copy">No summary available</p>}

      {safeItems.length > 0 && (
        <ul className="bullet-list">
          {safeItems.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
