import ChartTile from "./ChartTile";

export default function ChartGrid({ tab, panels, focusedPanelId, onSelectPanel }) {
  const safePanels = Array.isArray(panels) ? panels.filter(Boolean) : [];

  return (
    <section className={`quant-grid ${tab === "swing" ? "quant-grid-swing" : "quant-grid-intraday"}`}>
      {safePanels.map((panel, index) => (
        <ChartTile
          key={panel?.id || `${tab}-panel-${index}`}
          panel={panel}
          index={index}
          tab={tab}
          isFocused={panel?.id === focusedPanelId}
          onSelect={onSelectPanel}
        />
      ))}
    </section>
  );
}
