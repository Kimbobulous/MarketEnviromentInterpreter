# Market Environment Interpreter (MEI)
## Master Build Plan

---

# 1. Project Objective

Build a rule-based Market Environment Interpreter dashboard that:

- Separates Intraday vs Swing context
- Displays raw metrics → contextualized states → neutral interpretation
- Avoids prediction language
- Synthesizes dominant forces into structured summaries
- Remains deterministic and explainable

MVP priority:
Ship working vertical slices quickly and iterate.

---

# 2. Architecture Overview

## Frontend
- Next.js (App Router)
- Two Tabs:
  - Intraday
  - Swing
- Each tab contains:
  - Panels
  - Conditional Sensitivity section
  - Summary section

## Backend
- FastAPI (monolith)
- Deterministic compute layer
- Rule-based interpretation engine
- SQLite persistence (later milestone)
- Snapshot fallback logic (later milestone)

---

# 3. Milestone Roadmap

---

## Milestone 0 — Environment Setup
Status: ✅ COMPLETE

- [x] GitHub repo created
- [x] Dev branch created
- [x] Codespace configured
- [x] Codex authenticated
- [x] Folder structure initialized

---

## Milestone 1 — Backend API Skeleton
Status: ✅ COMPLETE

- [x] FastAPI service created
- [x] CORS configured
- [x] /api/intraday endpoint
- [x] /api/swing endpoint
- [x] Stub structured JSON returned
- [x] Port forwarding confirmed

---

## Milestone 2 — Frontend Initialization
Status: ✅ COMPLETE

Goal:
- Initialize Next.js inside /frontend
- Render basic page
- Confirm port 3000 works

Deliverable:
Basic frontend running in Codespace.

- [x] Next.js initialized in /frontend
- [x] Frontend runs in Codespaces on port 3000

---

## Milestone 3 — API ↔ UI Integration
Status: ✅ COMPLETE

Goal:
- Connect frontend to backend
- Fetch /api/intraday
- Render real panel data
- Handle loading states
- Confirm CORS behavior

Deliverable:
Intraday tab renders backend JSON.

- [x] Frontend fetches intraday JSON successfully
- [x] Next.js proxy route used to reach backend via localhost inside Codespace

---

## Milestone 4 — Compute Utility Layer
Status: ✅ COMPLETE

Goal:
- Rolling percentile function
- Regime classification (Low/Mid/High)
- Trend slope detection
- Deterministic unit tests

Deliverable:
Reusable compute module in backend/lib/.

- [x] `backend/lib/compute.py` (rolling_percentile, classify_regime, trend_slope)
- [x] Deterministic unit tests (pytest)
- [x] Compute integrated into stub payload generation for `/api/intraday` + `/api/swing`
- [x] Panel status handling (`ok`/`partial`/`error`) + computed sensitivity + summary
- [x] Refactor/shared builders to reduce duplication
- [x] Import/package fix (`backend` as package via `__init__.py`) so pytest works

---

## Milestone 5 — Interpretation Engine v1
Status: ✅ COMPLETE

Goal:
- Template-driven panel text generation
- Language guardrails
- Disallowed prediction word enforcement
- Conflict detection
- Summary synthesis

Deliverable:
Panel + tab summary generated from states.

- [x] `backend/lib/interpret.py` with `guard_language` + banned phrase list
- [x] Template-driven interpretation generation for all panels (intraday + swing)
- [x] Deterministic conflict/tension detection rules (adds `Tension:` line when applicable)
- [x] Tab-level summary synthesis: Overview / Regimes / Trends / Tensions / Notes with deterministic tie-breaks and banned-phrase compliance
- [x] Extended tests:
  - interpretation guardrail tests
  - tension detection tests
  - API payload tests validating summary structure + counts + banned-phrase scan
- [x] Test status: `pytest -q` (24 passed)

---

## Milestone 6 — SQLite Persistence
Status: ✅ COMPLETE

Goal:
- Snapshot storage
- Last-good fallback
- Audit log table

Deliverable:
Snapshots saved + recoverable.

- [x] SQLite `snapshots` table storing full payload JSON
- [x] Last-good fallback for `/api/intraday` and `/api/swing`
- [x] SQLite `audit_log` table with actions:
  - `snapshot_saved`
  - `build_failed`
  - `served_last_good`
- [x] Internal read-only endpoints:
  - `GET /api/snapshots/latest?tab=...&limit=...`
  - `GET /api/snapshots/{snapshot_id}`
  - `GET /api/audit?tab=...&limit=...`
- [x] Forced failure hook for deterministic tests: `MEI_FORCE_FAIL_TAB`
- [x] Tests added:
  - `backend/tests/test_persistence.py`
  - `backend/tests/test_snapshot_endpoints.py`
  - `backend/tests/test_last_good_fallback.py`
- [x] Test status: `pytest -q` (37 passed)

---

## Milestone 7 — Real Data (Intraday Core)
Status: ✅ COMPLETE

Goal:
- SPY daily OHLC
- VIX daily
- Yield proxy
- Rolling context windows
- Replace stub metrics

Deliverable:
Live data powering Intraday tab.

- [x] Massive/Polygon adapter + provider interface (SPY daily, VIX index daily)
- [x] FRED adapter for DGS10 yield series
- [x] SQLite `market_cache` table + caching layer
- [x] Intraday payload now powered by real daily series (SPY/VIX/DGS10) with compute metrics
- [x] `/api/market/status` endpoint reporting cache freshness + row counts
- [x] Interpretation updated to reference latest value + percentile/regime + trend/slope with language guardrails
- [x] Provider failure triggers last-good snapshot fallback (tested)
- [x] Test status: `pytest -q` (44 passed)

---

## Milestone 8 — Swing Panel Expansion
Status: ✅ COMPLETE

Goal:
- Breadth metrics
- Concentration proxy
- Sentiment inputs
- Volatility term structure

Deliverable:
Complete Swing tab panels.

- [x] Swing tab now computed with proxy panels:
  - Breadth Participation (RSP/SPY)
  - Concentration Tilt (QQQ/SPY)
  - Risk Sentiment (HYG/SHY)
  - Volatility Term Structure Proxy (VXX/VIX proxy)
- [x] Uses Massive/Polygon daily bars via adapter + SQLite cache
- [x] Interpretation engine applied to Swing panels with guardrails
- [x] Summary includes Swing proxy coverage line
- [x] Swing endpoint supports last-good snapshot fallback on provider failure (tested)
- [x] Tests/fixtures added for new tickers
- [x] Test status: `pytest -q` (52 passed)

---

## Milestone 9 — Summary Weighting Engine
Status: ✅ COMPLETE

Goal:
- Force weighting
- Dominant factor detection
- Structured 3–4 sentence output
- Mixed-signal acknowledgment

Deliverable:
Disciplined tab summary engine.

- [x] `backend/lib/weighting.py` force scoring + dominant factor detection + mixed-signal logic
- [x] Structured summary lines for intraday + swing: Lead / Support / Mixed (or Signal balance) / Scope + Diagnostics
- [x] Conditional sensitivity updated to be force-aware
- [x] Tests:
  - `test_weighting.py` unit coverage
  - API payload tests assert new summary format + guardrails
  - Fallback tests ensure Lead/Support survives last-good snapshots
- [x] Test status: `pytest -q` (58 passed)

---

## UI Milestone — Dark Quant UI + Chart-Dominant Layout
Status: ✅ COMPLETE

Deliverable:
Modern chart-dominant frontend with right-rail system insight and polished states.

- [x] Dark theme styling foundation across app shell and surfaces
- [x] TradingView Lightweight Charts integration
- [x] ChartTile + right-rail System Insight layout (chart-dominant)
- [x] Loading/error polish for dark theme UX
- [x] Dominant Force pill shown in UI
- [x] Sparklines shown per panel
- [x] Added `sparkline_times` to panels for time-aligned x-axis in charts (additive schema field)

---

## Refinement Milestone — Lookback Selector + Percentile Sanity + Provider Hardening
Status: ✅ COMPLETE

Deliverable:
User-selectable lookback windows, proxy-safe volatility source behavior, and debug percentile diagnostics.

- [x] Backend supports `lookback` query selector (`20/60/252`) on:
  - `GET /api/intraday`
  - `GET /api/swing`
- [x] Additive metadata emitted when selector is used:
  - `payload.window_meta.lookback_selected`
  - `panels[].window_meta.lookback_selected`
- [x] Frontend lookback selector implemented and wired through Next.js proxy routes
- [x] VIX index access hardening:
  - falls back to VIX proxy ticker (`VXX`) when index access returns provider `403`
  - labels explicitly indicate proxy usage (no index mislabeling)
- [x] `/api/market/status` expanded with per-source diagnostics + `last_error` + `label`
- [x] Added debug-only endpoint:
  - `GET /api/debug/percentile_sanity`
  - Reports percentile distribution summaries (min/max/mean and extreme-count diagnostics) for SPY, VXX, DGS10 across lookbacks 126 and 252

---

## Milestone 10 — Deployment
Status: ⏳ Pending

Goal:
- Production environment
- Environment variables
- Hosting setup
- Domain configuration

Deliverable:
Publicly accessible MEI dashboard.

---

# 4. Current Status

Current Milestone:
Post-Milestone Focus: UI/UX Upgrades (Dark Quant iteration)

Intraday and Swing are both powered by computed proxy-driven panels with persistence and fallback behavior.

UI Milestone:
Status: ✅ COMPLETE

- [x] Dark quant theme foundation and chart-dominant layout
- [x] Lightweight-charts integration with panel sparklines
- [x] Right-rail System Insight with dominant-force emphasis
- [x] Additive `sparkline_times` field used for time-aligned chart x-axis
- [x] Loading/error/collapsible interaction polish

Frontend:
Dashboard now uses a chart-first tile layout with a right-rail System Insight model, backed by existing proxy API routes.

---

# 5. Decisions / Notes

- Direct browser calls to the backend forwarded URL hit a 302 to github.dev/pf-signin in Codespaces, so we used a Next.js server-side proxy.
- Frontend now has Intraday/Swing tabs with correct layouts (2x2 intraday, 3+2 swing).
- PanelCard now renders sections A/B/C plus a "Why this matters" toggle.
- Conditional Sensitivity is collapsed by default and Summary is always visible.
- Next.js proxy routes exist for both `/api/intraday` and `/api/swing`.
- UI handles loading, error, and missing-panel states gracefully.
- VIX source behavior now explicitly supports proxy fallback (`VXX`) when index access is forbidden.
- Debug-only percentile diagnostics endpoint exists for distribution sanity checks:
  - `GET /api/debug/percentile_sanity`

---

# 6. Engineering Principles

- Ship vertical slices.
- Avoid overengineering.
- Deterministic over probabilistic.
- Neutral language only.
- No predictive framing.
- Keep infrastructure simple until necessary.

---

# 7. Next Immediate Action

Continue UI/UX upgrades:

- Add force weight visualization (bar/radar) in System Insight
- Add user-select ticker support (later phase)
