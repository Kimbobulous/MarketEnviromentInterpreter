# Milestone — Proper Quant Mode: Data Depth + Percentile Lock (Tasks 1–4)

## Objective
Move from partial/NA regime states to institutional-grade regime context by:
- fetching 252 daily bars (1Y) where possible
- using rolling percentile over a stable window (default 126; option 60)
- excluding current value from reference set (already intended)
- logging/returning enough metadata to verify bar counts and window usage
- adding deterministic tests to ensure behavior is stable and realistic

## Quant Standards (explicit)
- Fetch depth:
  - Pull 252 daily points where possible (target = 252, minimum acceptable = 120)
- Percentile context window:
  - Intraday: default 126 (6 months)
  - Swing: default 252 (1 year)
- Percentile calculation:
  - Percentile of latest value vs prior N values (exclude current)
  - If insufficient history (len(series) < N + 1), return None and mark panel "partial"

## Constraints
- No breaking API changes.
- Additive payload fields allowed.
- No new dependencies.
- Tests must be deterministic and offline (fixtures/mocks only).

---

## Task 1 — Ensure market providers fetch sufficient daily history

Modify:
- backend/lib/market_data/polygon_provider.py
- backend/lib/market_data/fred_provider.py
- backend/lib/market_data/client.py (if needed)

Requirements:
1) Add / enforce "limit" / "range" parameters so we fetch >= 252 daily points when available.
   - Polygon aggregates endpoint supports limit; request up to 252–300.
   - FRED: request at least 252 points (or 400) and slice down after.
2) Ensure returned series are ordered oldest -> newest.
3) Ensure client/cache stores:
   - series values
   - series dates
   - count (length)
4) For ratio series (swing panels):
   - Ensure intersection by date keeps oldest -> newest
   - Ensure you keep enough overlapping history (>= 252 if possible)

Acceptance:
- Internal series fetch functions can produce >=120 points when fixtures represent longer history.
- Ordering is always ascending by date.

Run pytest -q after changes.

---

## Task 2 — Lock lookback defaults + env overrides in one place

Modify:
- backend/main.py (or whichever module sets lookbacks)

Requirements:
1) Add env-overridable defaults (single source of truth):
   - MEI_INTRADAY_PCTL_LOOKBACK default 126
   - MEI_SWING_PCTL_LOOKBACK default 252
   - MEI_TREND_LOOKBACK default 126 (or 60 if you already chose 60; document)
   - MEI_SERIES_TARGET_BARS default 252
   - MEI_SERIES_MIN_BARS default 120
2) Ensure panels are computed as:
   - If series length < (pctl_lookback + 1) OR < trend_lookback:
       status = "partial"
       regime/trend/percentile fields omitted or set to None (consistent)
   - Else:
       status = "ok"

Acceptance:
- N/A/Unknown happens only when you truly lack history.
- With enough history, all panels become ok.

Run pytest -q.

---

## Task 3 — Add explicit debug metadata to each panel (additive)

Modify:
- backend/main.py (panel payload builder)

Add these OPTIONAL fields to each panel payload:
- "window_meta": {
    "series_points": <int>,
    "series_target": <int>,
    "series_min": <int>,
    "pctl_lookback": <int>,
    "trend_lookback": <int>,
    "pctl_excludes_current": true
  }

Also ensure:
- sparkline and sparkline_times are last <= 60 points (as today)
- but series_points refers to full fetched series length used for compute

Acceptance:
- Frontend can display why something is partial.
- No existing consumers break (additive fields only).

Update tests to allow this field but not require it unless you want to assert it exists.

Run pytest -q.

---

## Task 4 — Deterministic tests for “not always 0/100” and sufficient depth behavior

Modify/Create:
- backend/tests/test_compute.py
- backend/tests/test_intraday_real_data_integration.py
- backend/tests/test_swing_panels_integration.py
- backend/tests/fixtures/* (only if needed)

Add/extend tests:
1) rolling_percentile:
   - Excludes current
   - Non-monotonic series yields interior percentile (not 0/100)
   - Tie behavior stable (assert expected numeric value)
2) Integration (intraday & swing) with fixtures:
   - When fixtures include >252 points:
       - panel.status == "ok"
       - percentile exists and is within (0,100) for at least one panel
3) A regression guard:
   - Assert NOT all percentiles across panels are 0/100 when using rich fixtures.

Acceptance:
- pytest -q passes
- Summary remains structured
- No schema breaking changes

Return:
- list files changed
- pytest output
- sample /api/intraday panel window_meta for one panel (printed in code-run, not network)