"use client";

import { useEffect, useMemo, useRef, useState } from "react";

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

export default function InfoPill({ text, label = "Info", maxWidth = 320 }) {
  const triggerRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState({ top: 0, left: 0 });

  const safeText = useMemo(() => (typeof text === "string" ? text.trim() : ""), [text]);

  useEffect(() => {
    if (!open || !triggerRef.current) {
      return;
    }

    const rect = triggerRef.current.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const tooltipWidth = Math.min(maxWidth, viewportWidth - 24);
    const estimatedHeight = 120;

    const left = clamp(rect.left + rect.width / 2 - tooltipWidth / 2, 12, viewportWidth - tooltipWidth - 12);

    const showAbove = rect.top > estimatedHeight + 20;
    const top = showAbove ? rect.top - estimatedHeight - 10 : Math.min(rect.bottom + 10, viewportHeight - estimatedHeight - 10);

    setCoords({ top, left });
  }, [maxWidth, open, safeText]);

  if (!safeText) {
    return null;
  }

  return (
    <span
      style={{
        display: "inline-flex",
        position: "relative",
        marginLeft: 6,
        verticalAlign: "middle",
      }}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      <button
        ref={triggerRef}
        type="button"
        aria-label={label}
        style={{
          width: 16,
          height: 16,
          borderRadius: "50%",
          border: "1px solid #4e6f92",
          background: "#132135",
          color: "#d6e7ff",
          fontSize: 11,
          fontWeight: 700,
          lineHeight: "14px",
          textAlign: "center",
          cursor: "help",
          padding: 0,
        }}
      >
        ?
      </button>
      {open && (
        <div
          role="tooltip"
          style={{
            position: "fixed",
            left: coords.left,
            top: coords.top,
            zIndex: 200,
            width: `min(${maxWidth}px, calc(100vw - 24px))`,
            maxWidth: maxWidth,
            border: "1px solid #3d5d81",
            borderRadius: 10,
            background: "rgba(8, 15, 25, 0.98)",
            color: "#e6f0ff",
            padding: "0.55rem 0.65rem",
            boxShadow: "0 10px 24px rgba(0, 0, 0, 0.35)",
            fontSize: "0.74rem",
            lineHeight: 1.4,
            whiteSpace: "pre-line",
            pointerEvents: "none",
          }}
        >
          {safeText}
        </div>
      )}
    </span>
  );
}
