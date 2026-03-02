import { useState } from "react";
import { normalizeList } from "../../lib/normalize";

export default function SensitivitySection({ items }) {
  const [open, setOpen] = useState(false);
  const safeItems = normalizeList(items);

  return (
    <section className="dashboard-card section-card">
      <div className="section-header-row">
        <h2>Conditional Sensitivity</h2>
        <button type="button" className="ui-button" onClick={() => setOpen((prev) => !prev)}>
          {open ? "Hide" : "Show"}
        </button>
      </div>

      <div className={`accordion-wrap ${open ? "open" : ""}`}>
        {safeItems.length > 0 ? (
          <ul className="bullet-list">
            {safeItems.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        ) : (
          <p className="empty-copy">No conditional sensitivity available</p>
        )}
      </div>
    </section>
  );
}
