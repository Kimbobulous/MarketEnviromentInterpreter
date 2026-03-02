export default function MeiTabs({ activeTab, onChange }) {
  return (
    <div className="tab-shell" role="tablist" aria-label="MEI timeframe selector">
      <button
        type="button"
        role="tab"
        aria-selected={activeTab === "intraday"}
        className={`tab-pill ${activeTab === "intraday" ? "is-active" : ""}`}
        onClick={() => onChange("intraday")}
      >
        Intraday
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={activeTab === "swing"}
        className={`tab-pill ${activeTab === "swing" ? "is-active" : ""}`}
        onClick={() => onChange("swing")}
      >
        Swing
      </button>
    </div>
  );
}
