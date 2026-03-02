"use client";

import { AreaSeries, CrosshairMode, createChart } from "lightweight-charts";
import { useEffect, useMemo, useRef, useState } from "react";

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function toUnixSeconds(rawTime) {
  if (typeof rawTime === "number" && Number.isFinite(rawTime)) {
    return Math.floor(rawTime);
  }

  if (typeof rawTime === "string" && ISO_DATE_RE.test(rawTime)) {
    const parsed = Date.parse(`${rawTime}T00:00:00Z`);
    if (!Number.isNaN(parsed)) {
      return Math.floor(parsed / 1000);
    }
  }

  return null;
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

function buildSeriesData(data, times) {
  const source = Array.isArray(data) ? data : [];
  const values = source.filter((value) => typeof value === "number" && Number.isFinite(value));

  if (values.length < 1) {
    return [];
  }

  if (Array.isArray(times) && times.length === source.length) {
    const mapped = [];
    for (let index = 0; index < source.length; index += 1) {
      const value = source[index];
      const time = toUnixSeconds(times[index]);
      if (typeof value !== "number" || !Number.isFinite(value)) {
        continue;
      }
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

  const base = Math.floor(Date.now() / 1000) - (values.length - 1) * 60;
  const ordinal = values.map((value, index) => ({
    time: base + index * 60,
    value,
  }));
  return normalizeAndOrder(ordinal);
}

export default function SparklineTV({ data, times, height = 48, color = "#5aa8ff" }) {
  const containerRef = useRef(null);
  const dataPoints = useMemo(() => buildSeriesData(data, times), [data, times]);
  const [tooltip, setTooltip] = useState(null);

  useEffect(() => {
    if (!containerRef.current || dataPoints.length < 1) {
      return undefined;
    }

    const chart = createChart(containerRef.current, {
      autoSize: true,
      height,
      layout: {
        background: { color: "transparent" },
        textColor: "#95a7bd",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "rgba(42, 63, 88, 0.22)" },
        horzLines: { color: "rgba(42, 63, 88, 0.22)" },
      },
      rightPriceScale: {
        visible: true,
        borderVisible: true,
        scaleMargins: { top: 0.2, bottom: 0.2 },
      },
      leftPriceScale: {
        visible: false,
        borderVisible: false,
      },
      timeScale: {
        visible: true,
        borderVisible: true,
        rightOffset: 2,
        timeVisible: false,
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
      handleScroll: false,
      handleScale: false,
    });

    const areaOptions = {
      lineColor: color,
      lineWidth: 2,
      topColor: `${color}26`,
      bottomColor: `${color}02`,
      priceLineVisible: false,
      lastValueVisible: false,
    };
    const series =
      typeof chart.addSeries === "function"
        ? chart.addSeries(AreaSeries, areaOptions)
        : chart.addAreaSeries(areaOptions);

    series.setData(dataPoints);
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
        return;
      }

      const { x, y } = param.point;
      const width = containerRef.current.clientWidth;
      const heightPx = containerRef.current.clientHeight;
      if (x < 0 || y < 0 || x > width || y > heightPx) {
        setTooltip(null);
        return;
      }

      const pointData = param.seriesData?.get(series);
      const value =
        typeof pointData?.value === "number"
          ? pointData.value
          : typeof pointData?.close === "number"
            ? pointData.close
            : null;
      if (value === null) {
        setTooltip(null);
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

      const tipWidth = 170;
      const tipHeight = 44;
      const left = Math.max(8, Math.min(width - tipWidth - 8, x + 12));
      const top = Math.max(8, Math.min(heightPx - tipHeight - 8, y - tipHeight - 8));

      setTooltip({
        left,
        top,
        dateLabel: toDateLabel(param.time),
        valueLabel: formatValue(value),
        deltaText,
      });
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
      observer.disconnect();
      chart.remove();
    };
  }, [color, dataPoints, height]);

  if (dataPoints.length < 1) {
    return <div className="chart-empty">No chart data</div>;
  }

  return (
    <div style={{ position: "relative" }}>
      <div ref={containerRef} className="tv-sparkline" />
      {tooltip && (
        <div
          style={{
            position: "absolute",
            left: tooltip.left,
            top: tooltip.top,
            zIndex: 8,
            pointerEvents: "none",
            borderRadius: 8,
            border: "1px solid #2f4461",
            background: "rgba(9, 16, 27, 0.92)",
            color: "#dbe8fa",
            padding: "0.3rem 0.45rem",
            fontSize: "0.66rem",
            lineHeight: 1.25,
          }}
        >
          <div>{tooltip.dateLabel}</div>
          <div>Value: {tooltip.valueLabel}</div>
          {tooltip.deltaText && <div>Δ: {tooltip.deltaText}</div>}
        </div>
      )}
    </div>
  );
}
