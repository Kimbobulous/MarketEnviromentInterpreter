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
- GET /

Stub JSON structure (current truth):

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
- context[]
- interpretation[]
- why_toggle
- status
- last_updated

Backend currently returns stub data only.

---

## Frontend

Framework: Next.js (App Router)  
Language: JavaScript (.js), NOT TypeScript  
Location: /frontend  

Important:
- Do NOT introduce TypeScript
- Do NOT introduce Tailwind unless explicitly approved
- Do NOT add UI libraries
- Keep styling minimal

Frontend fetch rules:
- Browser calls:
  - /api/intraday
  - /api/swing
- Next.js route handlers proxy internally to:
  http://127.0.0.1:8000/...

Current status:
- Proxy working
- Tabs not yet implemented
- Dashboard layout scaffold in progress

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