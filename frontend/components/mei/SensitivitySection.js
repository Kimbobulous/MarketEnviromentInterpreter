import { useState } from "react";
import { normalizeList } from "../../lib/normalize";

const styles = {
  section: {
    border: "1px solid #d0d0d0",
    borderRadius: "6px",
    padding: "12px",
    marginTop: "12px",
    background: "#fafafa",
  },
  heading: {
    margin: "0 0 10px 0",
    fontSize: "16px",
  },
  toggleButton: {
    border: "1px solid #333",
    background: "#fff",
    padding: "6px 10px",
    cursor: "pointer",
    fontSize: "13px",
    marginBottom: "10px",
  },
  list: {
    margin: 0,
    paddingLeft: "18px",
  },
  listItem: {
    marginBottom: "4px",
    fontSize: "14px",
  },
  emptyText: {
    margin: 0,
    fontSize: "14px",
    color: "#666",
  },
};

export default function SensitivitySection({ items }) {
  const [open, setOpen] = useState(false);
  const safeItems = normalizeList(items);

  return (
    <section style={styles.section}>
      <h2 style={styles.heading}>Conditional Sensitivity</h2>
      <button
        type="button"
        style={styles.toggleButton}
        onClick={() => setOpen((prev) => !prev)}
      >
        {open ? "Hide conditional sensitivity" : "Show conditional sensitivity"}
      </button>

      {open &&
        (safeItems.length > 0 ? (
          <ul style={styles.list}>
            {safeItems.map((item, index) => (
              <li key={index} style={styles.listItem}>
                {item}
              </li>
            ))}
          </ul>
        ) : (
          <p style={styles.emptyText}>No conditional sensitivity available</p>
        ))}
    </section>
  );
}
