import { normalizeList } from "../../lib/normalize";

export default function SummarySection({ items }) {
  const safeItems = normalizeList(items);

  return (
    <section className="dashboard-card section-card">
      <div className="section-header-row">
        <h2>Summary</h2>
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
