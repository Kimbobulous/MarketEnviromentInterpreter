# Milestone — Dark Quant UI + Chart-Dominant Layout (Tasks 1–6)

## Objective
Refactor the MEI frontend UI into a modern 2026 dark quant platform:
- chart-dominant layout
- minimal chrome, strong hierarchy
- interactive charts with overlays for regime/trend/percentile
- right-rail “System Insight” showing dominant force + summary + tensions
- remove “card stack” aesthetic

## Constraints
- No backend changes required for this milestone.
- Keep existing API schema and routes.
- Prefer incremental refactor: old components may remain but should be unused by the end.
- Use TradingView Lightweight Charts (npm dependency).
- Keep it responsive (mobile: single column, desktop: 2-col with right rail).
- Keep loading/error states polished.

## Visual Direction (Dark Quant)
- Background: near-black (#0B0F14-ish)
- Surfaces: slightly lighter (#0F1620-ish) with subtle borders
- Typography: high-contrast but not pure white
- Accents:
  - Up: green
  - Down: red
  - Flat: blue/neutral
  - High regime: stronger accent
  - Low regime: muted accent
- Avoid “cards everywhere”; use “panels/surfaces” and chart tiles.

---

## Task 1 — Install charting + dark theme foundation

### Implementation
- Add dependency:
  - `lightweight-charts`
- Update global styles:
  - dark background
  - new surface styles
  - modern typography scale
  - utility classes for “surface”, “muted text”, “pill”, “divider”
- Ensure app looks correct with no charts yet.

### Acceptance
- App renders with dark theme globally.
- No white backgrounds.
- No layout regressions.

### Checkpoint
- run `npm run dev` and confirm basic page renders.

---

## Task 2 — Create Chart primitives (Lightweight Charts wrapper)

### Create
- `frontend/components/charts/SparklineTV.js` (or similar)
  - A reusable React component that renders a small line chart using lightweight-charts
  - props:
    - data: number[] (y-values)
    - height (default 48)
    - color (optional)
- `frontend/components/charts/SeriesChartTV.js`
  - Larger chart component:
    - data: number[] OR [{time, value}] (support both; if only number[], infer ordinal time)
    - height default 260
    - overlays:
      - top-left pill showing Regime + Trend
      - optional percentile meter

### Acceptance
- Chart components render without errors.
- Resize handling works (chart fits container).

---

## Task 3 — Build new layout shell (TopBar + Tabs + RightRail)

### Create/Modify
- Refactor homepage into a new layout:
  - TopBar:
    - Title
    - Tab switcher (Intraday/Swing)
    - last updated timestamp
  - Main grid:
    - Left: ChartGrid (dominant)
    - Right: System Insight rail (fixed on desktop, collapsible on mobile)

### Remove usage of old “PanelCard” layout from page rendering (can leave files in repo but not used).

### Acceptance
- No “Missing panel”.
- Desktop: two-column layout with right rail.
- Mobile: stacks.

---

## Task 4 — ChartTiles for panels (replaces cards)

### Create
- `frontend/components/mei/ChartTile.js`
  - Renders:
    - panel title
    - status badge
    - lightweight-charts mini chart using panel.sparkline
    - overlay pills for:
      - regime (Low/Mid/High)
      - trend (Up/Down/Flat)
      - percentile (as small horizontal meter)
    - metric highlights (2–3 key metrics) inline, not a table

### Layout rules
- Intraday:
  - 3 tiles in a 2x2-like grid (one empty not shown)
  - Consider one “primary” tile bigger: SPY
- Swing:
  - 4 tiles in a 2x2 grid on desktop (or 3+1)
  - Responsive to 1-column on mobile

### Acceptance
- Tiles feel like modern “surfaces”, not cards.
- Charts are the main element in each tile.
- Overlays reflect regime/trend visually (color semantics).

---

## Task 5 — System Insight rail (dominant force + summary + tensions)

### Modify/Create
- `frontend/components/mei/SystemInsight.js`
  - Shows:
    - Dominant Force (big pill)
    - Strength (strong/moderate/mixed)
    - Mixed-signal indicator if present
    - Summary lines (Lead/Support/Mixed/Scope)
    - Diagnostics collapsible (hide by default)
    - Conditional sensitivity collapsible

### Acceptance
- System Insight feels like the “brain” of the app.
- Summary is readable and visually prioritized.

---

## Task 6 — UX polish + states

### Requirements
- Loading:
  - show chart skeletons (shimmer) in tiles and right rail
- Error:
  - dark-themed error toast/banner with retry
- Micro-interactions:
  - hover elevation on tiles
  - subtle transitions on tab switch
  - collapsibles animate

### Acceptance
- The app feels premium and interactive.
- No jarring flashes.

---

## Validation Checklist (manual)
- `npm run dev`
- Both tabs render:
  - Intraday: 3 tiles with charts + right rail summary
  - Swing: 4 tiles with charts + right rail summary
- Stop backend:
  - error UI appears + retry works
- Confirm no “Missing panel” anywhere.

---

## Execution instructions to Codex
Implement Tasks 1–6 in order.
After each task:
- run `npm run dev` smoke check
Stop and fix issues before continuing.
Return:
- files changed
- any notes on layout decisions