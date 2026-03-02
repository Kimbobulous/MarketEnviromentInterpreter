"use client";

import { LineSeries, createChart } from "lightweight-charts";
import { useEffect, useMemo, useRef } from "react";

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
}) {
  const containerRef = useRef(null);
  const dataPoints = useMemo(() => normalizeSeriesData(data, timeLabels), [data, timeLabels]);

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
      },
      grid: {
        vertLines: { color: "rgba(42, 63, 88, 0.35)" },
        horzLines: { color: "rgba(42, 63, 88, 0.35)" },
      },
      rightPriceScale: {
        borderVisible: false,
      },
      leftPriceScale: {
        visible: false,
        borderVisible: false,
      },
      timeScale: {
        borderVisible: false,
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

    const observer = new ResizeObserver(() => {
      if (!containerRef.current) {
        return;
      }
      chart.applyOptions({ width: containerRef.current.clientWidth });
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
    };
  }, [color, dataPoints, height]);

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

      <div ref={containerRef} className="tv-series" />

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
