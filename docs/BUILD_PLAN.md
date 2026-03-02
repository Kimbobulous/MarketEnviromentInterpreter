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
Status: ⏳ Pending

Goal:
- Force weighting
- Dominant factor detection
- Structured 3–4 sentence output
- Mixed-signal acknowledgment

Deliverable:
Disciplined tab summary engine.

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
Milestone 9 — Summary Weighting Engine

Intraday and Swing are both powered by computed proxy-driven panels with persistence and fallback behavior.

UI Polish Milestone:
Status: ✅ COMPLETE

- [x] Modern global styling baseline (typography, tinted background, cards, badges, buttons)
- [x] Segmented tabs styling (Intraday/Swing)
- [x] Panel cards with improved hierarchy and "Why this matters" accordion
- [x] Raw metrics rendered as key/value rows
- [x] Responsive grids (no "Missing panel" placeholders)
- [x] Skeleton loading + error banner + retry
- [x] Sensitivity + Summary sections restyled

Frontend:
Dashboard UI scaffold complete with Intraday/Swing tabs, panel layouts, PanelCard sections, and shared sensitivity/summary rendering via proxy-backed API routes.

---

# 5. Decisions / Notes

- Direct browser calls to the backend forwarded URL hit a 302 to github.dev/pf-signin in Codespaces, so we used a Next.js server-side proxy.
- Frontend now has Intraday/Swing tabs with correct layouts (2x2 intraday, 3+2 swing).
- PanelCard now renders sections A/B/C plus a "Why this matters" toggle.
- Conditional Sensitivity is collapsed by default and Summary is always visible.
- Next.js proxy routes exist for both `/api/intraday` and `/api/swing`.
- UI handles loading, error, and missing-panel states gracefully.

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

Begin Milestone 9 Task 1: implement force weighting + dominant factor detection feeding a structured 3–4 sentence summary.
