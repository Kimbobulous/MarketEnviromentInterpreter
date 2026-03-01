const styles = {
  tabs: {
    display: "flex",
    gap: "8px",
    marginBottom: "12px",
  },
  button: {
    border: "1px solid #333",
    background: "#fff",
    color: "#222",
    padding: "8px 12px",
    cursor: "pointer",
  },
  activeButton: {
    background: "#222",
    color: "#fff",
  },
};

export default function MeiTabs({ activeTab, onChange }) {
  return (
    <div style={styles.tabs}>
      <button
        type="button"
        style={{
          ...styles.button,
          ...(activeTab === "intraday" ? styles.activeButton : {}),
        }}
        onClick={() => onChange("intraday")}
      >
        Intraday
      </button>
      <button
        type="button"
        style={{
          ...styles.button,
          ...(activeTab === "swing" ? styles.activeButton : {}),
        }}
        onClick={() => onChange("swing")}
      >
        Swing
      </button>
    </div>
  );
}
