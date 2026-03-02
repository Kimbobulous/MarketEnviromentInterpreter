# MEI Project Context
(Current authoritative system state)

---

## Environment

- Running in GitHub Codespaces
- Backend and frontend run concurrently
- Backend on port 8000
- Frontend on port 3000
- Browser must NEVER call the public 8000.app.github.dev URL directly
- All browser calls go through Next.js proxy routes

---

## Backend

Framework: FastAPI  
Location: /backend  
Entry: main.py  

Endpoints:
- GET /api/intraday
- GET /api/swing
- GET /api/market/status
- GET /api/snapshots/latest
- GET /api/snapshots/{snapshot_id}
- GET /api/audit
- GET /

Data + compute pipeline (current truth):
- Real market data providers are active:
  - Massive/Polygon (daily OHLC for SPY/VIX and swing proxy tickers)
  - FRED (macro yield series, default DGS10)
- SQLite-backed market cache is active (`market_cache` table).
- Snapshot persistence is active (`snapshots` + `audit_log`).
- Last-good fallback is active for both `/api/intraday` and `/api/swing` if a build/provider failure occurs.
- `/api/intraday` and `/api/swing` return computed panel outputs (not stub-only payloads).
- Summary weighting engine is active and emits structured summary lines:
  - `Lead`
  - `Support`
  - `Mixed` (or signal-balance equivalent)
  - `Scope`
  - `Diagnostics`

Payload shape:

payload:
- tab
- last_updated
- panels[]
- conditional_sensitivity[]
- summary[]

panel:
- id
- title
- raw_metrics[]
- sparkline[] (last <= 60 points)
- sparkline_times[] (aligned date labels for sparkline)
- context[]
- interpretation[]
- why_toggle
- status
- last_updated
- window_meta (additive debug metadata when present; non-breaking)

---

## Frontend

Framework: Next.js (App Router)  
Language: JavaScript (.js), NOT TypeScript  
Location: /frontend  

Important:
- Do NOT introduce TypeScript
- Do NOT introduce Tailwind unless explicitly approved
- `lightweight-charts` is already approved and in use (v5) for chart rendering.
- Do NOT add random/new UI dependencies without explicit approval.

Frontend fetch rules:
- Browser calls:
  - /api/intraday
  - /api/swing
- Next.js route handlers proxy internally to:
  http://127.0.0.1:8000/...

Current status:
- Proxy working
- Intraday and Swing tabs implemented
- Dark quant theme implemented
- Chart-dominant layout implemented
- Focused chart + stats/summary UI states implemented

---

## Git Rules

- Never commit:
  - frontend/node_modules
  - frontend/.next
  - backend/.venv
- Always commit at milestone completion
- Always push to origin dev

---

## Design Philosophy

- Ship MVP first
- No over-engineering
- No abstraction layers unless necessary
- Build incrementally
- One feature per Codex run
