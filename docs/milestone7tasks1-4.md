# Milestone 7 — Real Data (Intraday Core) — Tasks 1–4

## Global Constraints
- Do NOT change /api/intraday schema (payload keys and panel keys must remain identical).
- /api/swing remains stubbed for this milestone.
- No new dependencies (stdlib only).
- All tests must be deterministic and MUST NOT perform network I/O.
- Use SQLite caching (market_cache) and Milestone 6 last-good snapshot fallback.

## Environment
- backend/.env contains:
  - MEI_POLYGON_API_KEY=...
  - MEI_FRED_API_KEY=...
- Use env vars:
  - MEI_SPY_TICKER default "SPY"
  - MEI_VIX_TICKER default "I:VIX"
  - MEI_YIELD_SERIES default "DGS10"
  - MEI_MARKET_CACHE_MAX_AGE_SECONDS default 3600
  - MEI_DB_PATH optional

If backend does not currently load .env, add a minimal stdlib dotenv loader.

---

## Task 1 — Provider Adapters + Cached Real Data → Intraday Panels

### Create market data module structure
Create:
- backend/lib/env.py
  - load_dotenv(path): parse KEY=VALUE, ignore comments, do not overwrite existing os.environ
- backend/lib/market_data/base.py
  - MarketDataProvider interface with get_daily_ohlc(symbol, start=None, end=None)
- backend/lib/market_data/polygon_provider.py
  - Uses urllib.request to call Polygon/Massive Aggregates (daily bars):
    /v2/aggs/ticker/{ticker}/range/1/day/{from}/{to}?adjusted=true&sort=asc&limit=50000&apiKey=...
  - Converts results to rows:
    [{"date":"YYYY-MM-DD","open":..,"high":..,"low":..,"close":..,"volume":..}]
- backend/lib/market_data/fred_provider.py
  - Uses FRED observations endpoint to fetch DGS10 (configurable):
    https://api.stlouisfed.org/fred/series/observations?series_id=...&api_key=...&file_type=json
  - Returns rows [{"date":"YYYY-MM-DD","value":float}]
  - Skips missing values (".")
- backend/lib/market_data/cache.py
  - SQLite table market_cache(cache_key TEXT PRIMARY KEY, fetched_at TEXT, data_json TEXT)
  - cache_get(conn,key,max_age_seconds)->rows|None
  - cache_put(conn,key,rows)
- backend/lib/market_data/client.py
  - get_spy_daily(conn,...), get_vix_daily(conn,...), get_yield_daily(conn,...)
  - Uses cache + providers
  - Cache keys should include provider + symbol + date range for correctness

### Modify DB init
- Ensure backend/lib/db.py init_db creates market_cache table if missing.

### Integrate into /api/intraday
- In backend/main.py startup (lifespan preferred):
  - load_dotenv(backend/.env)
  - init_db
- In intraday payload builder:
  - Fetch SPY, VIX, DGS10 series through client (cached)
  - Build numeric series arrays (spy_close, vix_close, yield_value)
  - Use existing compute utils:
    - rolling_percentile(series, 20)
    - classify_regime(pct)
    - trend_slope(series[-60:])
    - trend_direction from slope sign
  - Build at least 3 intraday panels (SPY, VIX, Yield)
  - Keep panel schema identical
  - If insufficient data: panel.status="partial" and metric values None but keys present
  - If provider fetch fails: raise exception so last-good fallback triggers (Milestone 6)

### Tests (offline)
Create:
- backend/tests/fixtures/polygon_spy_aggs.json
- backend/tests/fixtures/polygon_vix_aggs.json
- backend/tests/fixtures/fred_dgs10.json
Create tests:
- backend/tests/test_market_data_providers.py
  - monkeypatch urllib.request.urlopen to return fixture JSON
  - test polygon provider parses rows + date conversion
  - test fred provider parses values and skips "."
  - test cache get/put with temp db
- backend/tests/test_intraday_real_data_integration.py
  - monkeypatch client.get_* to return deterministic rows
  - call get_intraday()
  - assert schema unchanged + compute keys present
  - ensure no network calls occur

Run pytest -q; stop and fix before Task 2.

---

## Task 2 — Observability Endpoint: /api/market/status

Add read-only endpoint:
- GET /api/market/status
Returns:
{
  "sources": {
    "spy": {"provider":"polygon","ticker":"SPY","cached":true,"age_seconds":123,"fetched_at":"...","rows":252},
    "vix": {...},
    "yield": {...}
  }
}

Implementation:
- Add helper in market_data/cache.py to return fetched_at for a cache key.
- Use MEI_MARKET_CACHE_MAX_AGE_SECONDS to compute freshness.
- No schema changes elsewhere.

Tests:
- backend/tests/test_market_status_endpoint.py
  - seed cache entries in temp db
  - call endpoint function
  - assert keys present and age_seconds computed

Run pytest -q; stop and fix before Task 3.

---

## Task 3 — Data-driven Interpretation for Intraday Panels

Update interpretation generation so intraday panel context/interpretation references:
- latest close/value
- percentile/regime
- trend direction/slope

Constraints:
- Must pass guard_language (no banned phrases)
- Deterministic output

Tests:
- Extend test_interpret.py or add test ensuring intraday interpretations mention regime/trend and contain no banned phrases.

Run pytest -q; stop and fix before Task 4.

---

## Task 4 — Persistence + Fallback Verification (Real data path)

Ensure:
- /api/intraday saves snapshot when real data fetch succeeds
- forced failure via MEI_FORCE_FAIL_TAB=intraday still serves last-good snapshot
- add test that simulates provider failure (mock urlopen to raise) and asserts last-good served (if exists) + audit events recorded

Tests:
- extend backend/tests/test_last_good_fallback.py (or new) with provider failure mock

Run pytest -q; must be green.

---

## Acceptance Criteria (Milestone 7)
- /api/intraday is powered by real data (SPY, VIX, DGS10) via adapters + SQLite cache
- /api/swing unchanged
- Offline deterministic tests pass; no network calls during tests
- /api/market/status works
- Interpretation is data-driven and guardrailed
- Persistence + fallback works under provider failure