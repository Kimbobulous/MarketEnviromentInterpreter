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
Status: ⏳ IN PROGRESS

Goal:
- Initialize Next.js inside /frontend
- Render basic page
- Confirm port 3000 works

Deliverable:
Basic frontend running in Codespace.

---

## Milestone 3 — API ↔ UI Integration
Status: ⏳ Pending

Goal:
- Connect frontend to backend
- Fetch /api/intraday
- Render real panel data
- Handle loading states
- Confirm CORS behavior

Deliverable:
Intraday tab renders backend JSON.

---

## Milestone 4 — Compute Utility Layer
Status: ⏳ Pending

Goal:
- Rolling percentile function
- Regime classification (Low/Mid/High)
- Trend slope detection
- Deterministic unit tests

Deliverable:
Reusable compute module in backend/lib/.

---

## Milestone 5 — Interpretation Engine v1
Status: ⏳ Pending

Goal:
- Template-driven panel text generation
- Language guardrails
- Disallowed prediction word enforcement
- Conflict detection
- Summary synthesis

Deliverable:
Panel + tab summary generated from states.

---

## Milestone 6 — SQLite Persistence
Status: ⏳ Pending

Goal:
- Snapshot storage
- Last-good fallback
- Audit log table

Deliverable:
Snapshots saved + recoverable.

---

## Milestone 7 — Real Data (Intraday Core)
Status: ⏳ Pending

Goal:
- SPY daily OHLC
- VIX daily
- Yield proxy
- Rolling context windows
- Replace stub metrics

Deliverable:
Live data powering Intraday tab.

---

## Milestone 8 — Swing Panel Expansion
Status: ⏳ Pending

Goal:
- Breadth metrics
- Concentration proxy
- Sentiment inputs
- Volatility term structure

Deliverable:
Complete Swing tab panels.

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
Milestone 2 — Frontend Initialization

Backend:
Fully operational skeleton.

Frontend:
Not yet initialized.

---

# 5. Engineering Principles

- Ship vertical slices.
- Avoid overengineering.
- Deterministic over probabilistic.
- Neutral language only.
- No predictive framing.
- Keep infrastructure simple until necessary.

---

# 6. Next Immediate Action

Initialize Next.js inside /frontend.
Confirm it runs on port 3000.