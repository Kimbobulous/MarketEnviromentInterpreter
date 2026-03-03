# MEI Development Setup

## Environment

- GitHub Codespaces
- Backend: FastAPI (port 8000)
- Frontend: Next.js (port 3000)

---
## Signle start up command

From repo root:

    npm run dev:all

If this is the first time after cloning (or after pulling new deps):

    npm install
    npm run dev:all

## Starting the Backend

From repo root:

cd backend
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Backend runs on:
http://localhost:8000

---

## Starting the Frontend

From repo root:

cd frontend
npm run dev -- --port 3000

Frontend runs on:
http://localhost:3000

---

## Codespaces Rules

- Always run backend and frontend in separate terminals.
- Browser calls frontend (port 3000).
- Frontend calls backend via internal proxy.
- Never call public 8000.app.github.dev from browser code.

---

## After Codespace Restart

Run backend first.
Then run frontend.