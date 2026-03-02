"use client";

import { CrosshairMode, LineSeries, createChart } from "lightweight-charts";
import { useEffect, useMemo, useRef, useState } from "react";

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function normalizeTime(value, fallback) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return Math.floor(value);
  }

  if (typeof value === "string" && ISO_DATE_RE.test(value)) {
    const parsed = Date.parse(`${value}T00:00:00Z`);
    if (!Number.isNaN(parsed)) {
      return Math.floor(parsed / 1000);
    }
  }

  return fallback;
}

function normalizeAndOrder(points) {
  const clean = points
    .filter(
      (point) =>
        point &&
        typeof point === "object" &&
        typeof point.value === "number" &&
        Number.isFinite(point.value) &&
        typeof point.time === "number" &&
        Number.isFinite(point.time)
    )
    .map((point, index) => ({
      time: Math.floor(point.time),
      value: point.value,
      index,
    }));

  clean.sort((a, b) => a.time - b.time || a.index - b.index);

  const deduped = [];
  for (const point of clean) {
    const last = deduped[deduped.length - 1];
    if (last && last.time === point.time) {
      deduped[deduped.length - 1] = { time: point.time, value: point.value };
    } else {
      deduped.push({ time: point.time, value: point.value });
    }
  }

  return deduped;
}

function toDateLabel(rawTime) {
  if (typeof rawTime === "number" && Number.isFinite(rawTime)) {
    return new Date(rawTime * 1000).toISOString().slice(0, 10);
  }

  if (rawTime && typeof rawTime === "object") {
    const y = rawTime.year;
    const m = rawTime.month;
    const d = rawTime.day;
    if ([y, m, d].every((value) => typeof value === "number")) {
      return `${y.toString().padStart(4, "0")}-${m.toString().padStart(2, "0")}-${d
        .toString()
        .padStart(2, "0")}`;
    }
  }

  return "N/A";
}

function formatValue(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "N/A";
  }
  if (Math.abs(value) >= 100) {
    return value.toFixed(2);
  }
  if (Math.abs(value) >= 10) {
    return value.toFixed(3);
  }
  return value.toFixed(4);
}

function normalizeSeriesData(data, timeLabels) {
  if (!Array.isArray(data)) {
    return [];
  }

  const numericOnly = data.every((item) => typeof item === "number" && Number.isFinite(item));
  if (numericOnly) {
    const points = data;
    if (points.length < 1) {
      return [];
    }

    if (Array.isArray(timeLabels) && timeLabels.length === points.length) {
      const mapped = [];
      for (let index = 0; index < points.length; index += 1) {
        const time = normalizeTime(timeLabels[index], null);
        const value = points[index];
        if (time === null) {
          continue;
        }
        mapped.push({ time, value });
      }
      const normalized = normalizeAndOrder(mapped);
      if (normalized.length >= 1) {
        return normalized;
      }
    }

    const base = Math.floor(Date.now() / 1000) - (points.length - 1) * 60;
    return normalizeAndOrder(points.map((value, index) => ({ time: base + index * 60, value })));
  }

  const mapped = [];
  for (let index = 0; index < data.length; index += 1) {
    const item = data[index];
    if (!item || typeof item !== "object") {
      continue;
    }

    const rawValue = item.value;
    if (typeof rawValue !== "number" || !Number.isFinite(rawValue)) {
      continue;
    }

    const fallbackTime = Math.floor(Date.now() / 1000) - (data.length - index) * 60;
    mapped.push({
      time: normalizeTime(item.time, fallbackTime),
      value: rawValue,
    });
  }

  return normalizeAndOrder(mapped);
}

function trendClass(trend) {
  const key = String(trend || "").toLowerCase();
  if (key === "up") return "up";
  if (key === "down") return "down";
  return "flat";
}

export default function SeriesChartTV({
  data,
  timeLabels,
  height = 260,
  regime,
  trend,
  percentile,
  color = "#5aa8ff",
  showFloatingTooltip = true,
  onHoverChange,
}) {
  const containerRef = useRef(null);
  const dataPoints = useMemo(() => normalizeSeriesData(data, timeLabels), [data, timeLabels]);
  const [tooltip, setTooltip] = useState(null);

  useEffect(() => {
    if (!containerRef.current || dataPoints.length < 1) {
      if (typeof onHoverChange === "function") {
        onHoverChange(null);
      }
      return undefined;
    }

    const chart = createChart(containerRef.current, {
      autoSize: true,
      height,
      layout: {
        background: { color: "transparent" },
        textColor: "#95a7bd",
        fontSize: 12,
      },
      grid: {
        vertLines: { color: "rgba(42, 63, 88, 0.35)" },
        horzLines: { color: "rgba(42, 63, 88, 0.35)" },
      },
      rightPriceScale: {
        visible: true,
        borderVisible: false,
        scaleMargins: { top: 0.14, bottom: 0.14 },
      },
      leftPriceScale: {
        visible: false,
        borderVisible: false,
      },
      timeScale: {
        visible: true,
        borderVisible: false,
        rightOffset: 2,
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          visible: true,
          color: "rgba(132, 173, 216, 0.5)",
          width: 1,
        },
        horzLine: {
          visible: true,
          color: "rgba(132, 173, 216, 0.42)",
          width: 1,
        },
      },
    });

    const lineOptions = {
      color,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    };
    const lineSeries =
      typeof chart.addSeries === "function"
        ? chart.addSeries(LineSeries, lineOptions)
        : chart.addLineSeries(lineOptions);

    lineSeries.setData(dataPoints);
    if (dataPoints.length >= 2) {
      chart.timeScale().fitContent();
    }

    const previousByTime = new Map();
    for (let index = 1; index < dataPoints.length; index += 1) {
      previousByTime.set(dataPoints[index].time, dataPoints[index - 1].value);
    }

    const handleCrosshairMove = (param) => {
      if (!containerRef.current || !param || !param.point || !param.time) {
        setTooltip(null);
        if (typeof onHoverChange === "function") {
          onHoverChange(null);
        }
        return;
      }

      const { x, y } = param.point;
      const width = containerRef.current.clientWidth;
      const heightPx = containerRef.current.clientHeight;
      if (x < 0 || y < 0 || x > width || y > heightPx) {
        setTooltip(null);
        if (typeof onHoverChange === "function") {
          onHoverChange(null);
        }
        return;
      }

      const pointData = param.seriesData?.get(lineSeries);
      const value =
        typeof pointData?.value === "number"
          ? pointData.value
          : typeof pointData?.close === "number"
            ? pointData.close
            : null;
      if (value === null) {
        setTooltip(null);
        if (typeof onHoverChange === "function") {
          onHoverChange(null);
        }
        return;
      }

      const epochTime =
        typeof param.time === "number" && Number.isFinite(param.time)
          ? Math.floor(param.time)
          : null;
      const previousValue = epochTime !== null ? previousByTime.get(epochTime) : undefined;
      const deltaText =
        typeof previousValue === "number" && Number.isFinite(previousValue)
          ? `${value >= previousValue ? "+" : ""}${(value - previousValue).toFixed(4)}`
          : null;

      const tipWidth = 196;
      const tipHeight = 64;
      const left = Math.max(8, Math.min(width - tipWidth - 8, x + 12));
      const top = Math.max(8, Math.min(heightPx - tipHeight - 8, y - tipHeight - 10));

      const nextHover = {
        left,
        top,
        dateLabel: toDateLabel(param.time),
        valueLabel: formatValue(value),
        deltaText,
      };
      setTooltip(nextHover);
      if (typeof onHoverChange === "function") {
        onHoverChange({
          dateLabel: nextHover.dateLabel,
          valueLabel: nextHover.valueLabel,
          deltaText: nextHover.deltaText,
        });
      }
    };
    chart.subscribeCrosshairMove(handleCrosshairMove);

    const observer = new ResizeObserver(() => {
      if (!containerRef.current) {
        return;
      }
      chart.applyOptions({ width: containerRef.current.clientWidth });
    });
    observer.observe(containerRef.current);

    return () => {
      chart.unsubscribeCrosshairMove(handleCrosshairMove);
      setTooltip(null);
      if (typeof onHoverChange === "function") {
        onHoverChange(null);
      }
      observer.disconnect();
      chart.remove();
    };
  }, [color, dataPoints, height, onHoverChange]);

  if (dataPoints.length < 1) {
    return <div className="chart-empty chart-large-empty">No chart data</div>;
  }

  const safePercentile =
    typeof percentile === "number" && Number.isFinite(percentile)
      ? Math.max(0, Math.min(100, percentile))
      : null;

  return (
    <div className="tv-series-wrap">
      <div className="tv-overlay-row">
        <span className={`pill tv-trend-pill trend-${trendClass(trend)}`}>
          {String(regime || "Unknown")} · {String(trend || "Flat")}
        </span>
      </div>

      <div style={{ position: "relative" }}>
        <div ref={containerRef} className="tv-series" />
        {showFloatingTooltip && tooltip && (
          <div
            style={{
              position: "absolute",
              left: tooltip.left,
              top: tooltip.top,
              zIndex: 12,
              pointerEvents: "none",
              borderRadius: 10,
              border: "1px solid #355173",
              background: "rgba(9, 16, 27, 0.95)",
              color: "#deebfc",
              padding: "0.42rem 0.55rem",
              fontSize: "0.72rem",
              lineHeight: 1.35,
              minWidth: 170,
            }}
          >
            <div>{tooltip.dateLabel}</div>
            <div>Value: {tooltip.valueLabel}</div>
            {tooltip.deltaText && <div>Δ: {tooltip.deltaText}</div>}
          </div>
        )}
      </div>

      {safePercentile !== null && (
        <div className="tv-percentile-meter" aria-label={`Percentile ${safePercentile.toFixed(0)}`}>
          <span>Percentile</span>
          <div className="tv-percentile-track">
            <div className="tv-percentile-fill" style={{ width: `${safePercentile}%` }} />
          </div>
          <strong>{safePercentile.toFixed(0)}</strong>
        </div>
      )}
    </div>
  );
}
