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
  paragraph: {
    margin: 0,
    fontSize: "14px",
    lineHeight: 1.4,
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

export default function SummarySection({ items }) {
  const safeItems = normalizeList(items);

  return (
    <section style={styles.section}>
      <h2 style={styles.heading}>Summary</h2>
      {safeItems.length === 0 && <p style={styles.emptyText}>No summary available</p>}

      {safeItems.length === 1 && <p style={styles.paragraph}>{safeItems[0]}</p>}

      {safeItems.length > 1 && (
        <ul style={styles.list}>
          {safeItems.map((item, index) => (
            <li key={index} style={styles.listItem}>
              {item}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
