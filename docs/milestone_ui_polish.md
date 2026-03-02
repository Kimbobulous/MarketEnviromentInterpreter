# Milestone — UI Polish & Modern Dashboard UX (Tasks 1–4)

## Objective
Upgrade the MEI dashboard UI from a plain “debug layout” into a modern 2026-style web app:
- clean typography, spacing, and hierarchy
- polished cards, badges, empty states
- skeleton loading states
- responsive layout that never shows “Missing panel” placeholder
- consistent structure across Intraday/Swing

## Constraints
- Do NOT change backend APIs.
- Do NOT change payload schema.
- Keep current components but refactor as needed.
- Avoid heavy dependencies unless already installed.
- Prefer Tailwind if it’s already configured; otherwise use a single global CSS file + CSS modules.
- Do not over-engineer: ship a clean MVP UI.

## UX Requirements
- The app should feel like a modern dashboard:
  - centered max-width container (1100–1200px)
  - modern font stack
  - subtle background tint
  - cards with soft border + slight shadow
  - clear section headers (Raw Metrics / Context / Interpretation / Why this matters)
  - status badges: ok (green), partial (amber), error (red)
- Layout:
  - Intraday: 2-column grid on desktop, 1-column on mobile
  - Swing: 3-column grid on desktop, 1-column on mobile, 2-column on medium
  - Never show “Missing panel”. If fewer panels than layout slots, just render the panels you have.
- Content formatting:
  - Raw metrics should display as key/value rows, not JSON-like text
  - Lists (context/interpretation/summary) should have consistent bullet styling
- Loading & error:
  - show skeleton placeholders while fetching
  - show a clean inline error banner on fetch failure with a “Retry” button
  - allow partial payloads to render what’s available

## Task 1 — Global styling foundation
### Goal
Add a modern global style baseline (either Tailwind usage cleanup or a global CSS file).

Implementation
- Create or update:
  - frontend/app/globals.css (preferred in Next App Router)
  - Ensure it’s imported in frontend/app/layout.js (or layout.tsx)
- Add:
  - modern font stack, background color, default text color
  - headings spacing scale
  - card base class styles
  - badge styles
  - skeleton styles
  - buttons style

Acceptance checks
- Page background is not plain white
- Typography looks modern and consistent
- Cards have visual separation

## Task 2 — Component modernization (Panels + Tabs + Sections)
### Goal
Refactor UI components to render panels like a real dashboard.

Implementation
- Update / create components (where your MEI components live):
  - Tabs component:
    - pill-style segmented control
    - active tab filled
  - PanelCard component:
    - title row with status badge + last updated
    - sections:
      - Raw Metrics as a table-like list (two-column key/value)
      - Context and Interpretation as bullets
      - “Why this matters” as collapsible accordion/toggle (smooth open/close)
  - Summary component:
    - card container
    - bullet list styling
  - Conditional Sensitivity:
    - collapsible with cleaner styling

Acceptance checks
- No JSON pretty print anywhere
- Status is visually obvious
- Raw Metrics are readable at a glance

## Task 3 — Layout fixes + responsive grid + remove Missing panel
### Goal
Make the layout responsive and remove empty placeholder cards.

Implementation
- Replace fixed slot grids with rendering based on panels array length.
- Layout rules:
  - Intraday:
    - grid-cols-1 on mobile
    - grid-cols-2 on desktop
  - Swing:
    - grid-cols-1 mobile
    - grid-cols-2 medium
    - grid-cols-3 desktop
- Ensure Summary + Conditional Sensitivity sit below grid with consistent spacing.
- Remove “Missing panel” rendering entirely.

Acceptance checks
- No “Missing panel” anywhere
- Works nicely on narrow width
- Swing shows 4 panels in a clean grid without awkward empty boxes

## Task 4 — Loading/error states + small UX delights
### Goal
Upgrade perceived quality.

Implementation
- Add:
  - skeleton cards that match real card shapes while loading
  - error banner with retry button that re-triggers fetch
  - subtle transitions (hover shadow, accordion animation)
  - show “Fetching: /api/…” in a subtle secondary text style (or hide it behind a small “Data source” line)

Acceptance checks
- On refresh, skeleton appears briefly (or on slow network)
- If backend is down, error UI is clean and does not break layout
- Retry works

## Validation checklist (manual)
- Run backend on 8000, frontend on 3000
- Check:
  - Intraday tab renders 3 panels cleanly
  - Swing tab renders 4 panels cleanly
  - Toggle “Why this matters” works
  - Summary looks like a modern dashboard section
  - Loading skeleton shows
  - Error banner appears if backend stopped

## Execution instructions for Codex
Implement Tasks 1–4 in order.
After each task, run:
- frontend: `npm run lint` (if configured) and `npm run dev` smoke check
Stop and fix failures before continuing.
Return:
- list of files changed
- screenshots are optional, but describe the UI improvements in words