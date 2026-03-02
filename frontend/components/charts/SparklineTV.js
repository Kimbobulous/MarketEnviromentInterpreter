"use client";

import { AreaSeries, createChart } from "lightweight-charts";
import { useEffect, useMemo, useRef } from "react";

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
        vertLines: { color: "transparent" },
        horzLines: { color: "transparent" },
      },
      rightPriceScale: {
        visible: false,
        borderVisible: false,
      },
      leftPriceScale: {
        visible: false,
        borderVisible: false,
      },
      timeScale: {
        visible: false,
        borderVisible: false,
      },
      crosshair: {
        vertLine: { visible: false },
        horzLine: { visible: false },
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
    return <div className="chart-empty">No chart data</div>;
  }

  return <div ref={containerRef} className="tv-sparkline" />;
}
