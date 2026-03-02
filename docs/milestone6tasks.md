---

# Milestone 6 — Tasks 2–4 Spec (SQLite Persistence)

## Assumptions / Context

* Task 1 already implemented:

  * `backend/lib/db.py` with `get_db_path()`, `connect()`, `init_db()`
  * `backend/lib/snapshots.py` with `derive_payload_status()`, `save_snapshot()`, `get_last_good_snapshot()`, `log_action()`
  * `/api/intraday` writes snapshots and serves last-good on failure
  * Tests exist in `backend/tests/test_persistence.py`
* No external dependencies. Use Python stdlib only.
* DB path via `MEI_DB_PATH` env var; default `backend/data/mei.db`.

---

## Task 2 — Extend persistence + last-good fallback to Swing

### Goal

Apply the exact same snapshot + audit + last-good fallback flow to `/api/swing`.

### Requirements

1. In `backend/main.py` (or the module where endpoints are defined):

* Wrap the Swing payload build in try/except just like intraday.
* On success:

  * `save_snapshot(conn, tab="swing", payload)`
  * return payload
* On exception:

  * `log_action(... action="build_failed" ...)`
  * attempt `get_last_good_snapshot(conn, tab="swing")`
  * if found:

    * `log_action(... action="served_last_good" ...)`
    * return last snapshot payload
  * else re-raise or return 500 (match intraday behavior)

2. Ensure DB initialization happens once (startup event or module init), and both endpoints share that connection pattern.

### Tests (extend `backend/tests/test_persistence.py` or add `backend/tests/test_api_persistence.py`)

* Test that `save_snapshot` + `get_last_good_snapshot` works for `tab="swing"` as well.
* Add a lightweight integration-style test that calls `get_swing()` twice and verifies:

  * Snapshot count for “swing” increases (use a temp DB via `MEI_DB_PATH`).
  * Returned payload schema is unchanged.

> Note: If you don’t want to hit FastAPI via HTTP in tests, directly call the handler function (like you did in earlier API payload tests). The key is verifying snapshot persistence is triggered.

---

## Task 3 — Add internal snapshot retrieval endpoints (minimal, read-only)

### Goal

Provide basic observability and recoverability:

* list latest snapshots
* fetch snapshot by id
* view audit log entries

### Endpoints (add to `backend/main.py`)

**A) GET `/api/snapshots/latest`**

* Query params:

  * `tab` (required): `"intraday"` or `"swing"`
  * `limit` (optional, default 10, max 50)
* Returns JSON:

```json
{
  "tab": "intraday",
  "count": 3,
  "snapshots": [
    { "id": 12, "created_at": "...", "status": "ok" }
  ]
}
```

* This endpoint must **not** return `payload_json` to keep response small.

**B) GET `/api/snapshots/{snapshot_id}`**

* Returns:

```json
{
  "id": 12,
  "tab": "intraday",
  "created_at": "...",
  "status": "ok",
  "payload": { ...original payload... }
}
```

* If not found, return 404 JSON `{ "error": "not found" }`.

**C) GET `/api/audit`**

* Query params:

  * `tab` optional
  * `limit` optional default 50 max 200
* Returns:

```json
{
  "count": 20,
  "events": [
    { "id": 1, "created_at": "...", "tab": "intraday", "action": "snapshot_saved", "detail": "" }
  ]
}
```

### Implementation details

* Add read helpers to `backend/lib/snapshots.py` (or `db.py`) as needed:

  * `list_snapshots(conn, tab, limit)` returning metadata rows
  * `get_snapshot_by_id(conn, snapshot_id)`
  * `list_audit(conn, tab=None, limit=50)`

### Tests

Create `backend/tests/test_snapshot_endpoints.py` (or extend existing API tests) that:

* Uses a temp DB via env var `MEI_DB_PATH` (pytest `monkeypatch`).
* Inserts a few snapshots via `save_snapshot()`.
* Calls the endpoint functions directly (or via TestClient if you already use it; but no new deps).
* Asserts:

  * `/api/snapshots/latest` returns correct count and metadata keys
  * `/api/snapshots/{id}` returns payload and matches inserted payload
  * `/api/audit` returns events and includes “snapshot_saved”

---

## Task 4 — End-to-end fallback verification + guardrails

### Goal

Prove last-good fallback works in a deterministic test and add guardrails:

* Snapshot retrieval prefers last good status only (`ok` or `partial`)
* Errors still get logged
* Fallback is only used when build fails

### Implementation

1. Ensure `get_last_good_snapshot()` explicitly filters status in (`ok`, `partial`) and excludes `error`.
2. Add a deterministic way to simulate a build failure **without changing schema**:

* In `backend/main.py` intraday/swing handlers, add:

  * if env var `MEI_FORCE_FAIL_TAB` equals `"intraday"` or `"swing"`, raise `RuntimeError("forced failure")`
* This must be used only for tests (no user-facing docs needed).

3. Update fallback logic to:

* On forced failure:

  * log `build_failed`
  * return last-good if exists and log `served_last_good`
  * if none exists: propagate error (or 500), but ensure `build_failed` logged

### Tests (new `backend/tests/test_last_good_fallback.py`)

Use temp DB + monkeypatch env vars:

* Scenario 1: last-good exists

  1. Ensure `MEI_DB_PATH` points to temp db, initialize tables.
  2. Call `get_intraday()` once with `MEI_FORCE_FAIL_TAB` unset → snapshot saved.
  3. Set `MEI_FORCE_FAIL_TAB=intraday` and call `get_intraday()` again.
  4. Assert:

     * returned payload equals the previously saved payload (or matches by `last_updated`/panels)
     * audit log contains `build_failed` and `served_last_good`

* Scenario 2: no last-good exists

  1. Fresh temp db, set `MEI_FORCE_FAIL_TAB=intraday`
  2. Call `get_intraday()` and assert it raises or returns 500 (match your handler approach)
  3. Assert audit log contains `build_failed` only

* Scenario 3: last snapshot status=error should not be served

  1. Insert an “error” snapshot manually (call `save_snapshot` with payload having a panel status error)
  2. Force failure
  3. Assert:

     * fallback does not return the error snapshot
     * behavior matches “no last good” (raise/500)
     * audit log includes build_failed

### Acceptance criteria (for Tasks 2–4)

* `pytest -q` passes.
* `/api/intraday` and `/api/swing` both:

  * write snapshots on success
  * serve last-good on failure
  * log actions in audit
* Internal endpoints return expected metadata/payload.
* No schema changes to existing intraday/swing payloads.

---

## Commands to run

From repo root:

```bash
cd backend
source .venv/bin/activate
pytest -q
```

---

## What Codex should return

* List of changed files
* `pytest -q` output
* Example outputs:

  * `GET /api/snapshots/latest?tab=intraday`
  * `GET /api/snapshots/1` (or any id)
  * `GET /api/audit?limit=5`

---

