# Milestone 8 — Swing Panel Expansion (Tasks 1–4)

## Objective
Replace Swing tab stub panels with real computed panels for:
- Breadth metrics
- Concentration proxy
- Sentiment inputs
- Volatility term structure

Deliverable:
Swing tab panels populated with real-data-driven metrics and interpretations, using the same schema and guardrails as Intraday.

## Global Constraints
- DO NOT change /api/swing payload schema.
- Keep /api/intraday as-is (already real data).
- No new dependencies (stdlib only).
- All tests deterministic and MUST NOT perform network I/O.
- Use existing market_data adapter architecture:
  - Massive/Polygon provider
  - FRED provider (if needed)
  - SQLite market_cache
- Use existing compute + interpret:
  - rolling_percentile, classify_regime, trend_slope
  - generate_interpretation + detect_tensions + guard_language
- Maintain Milestone 6 snapshot persistence + last-good fallback on failure.

## Data choices for Swing (MVP-safe)
To avoid needing proprietary “breadth/concentration” datasets, we use practical proxies available via Massive daily bars:

1) Breadth proxy:
   - Use ratio or spread between equal-weight SP500 ETF and cap-weight SP500:
     - RSP (Invesco S&P 500 Equal Weight ETF)
     - SPY (SPDR S&P 500 ETF)
   - Breadth_strength_series = log(RSP_close / SPY_close)
   - Interprets: broad participation vs mega-cap dominance.

2) Concentration proxy:
   - Compare QQQ vs SPY (tech/mega-cap tilt proxy)
   - Concentration_series = log(QQQ_close / SPY_close)

3) Sentiment proxy:
   - Use Put/Call proxy is hard without options data, so use risk-on/off ETF ratio:
     - HYG (High Yield Corp Bond ETF) vs SHY (1-3y Treasury ETF) or TLT
   - Sentiment_series = log(HYG_close / SHY_close) (or /TLT if preferred)

4) Volatility term structure proxy:
   True VIX term structure requires VIX futures. For MVP:
   - Use VIX index level (I:VIX) and a short-term vol ETF proxy like VXX if available.
   - Term_structure_proxy = log(VXX_close / VIX_close) (fallback to only VIX if VXX unavailable)
   If VXX isn’t supported on free tier or unavailable, degrade gracefully:
   - Panel status = "partial"
   - Raw metrics values None where needed
   - Interpretation mentions unavailable series.

All tickers must be configurable via env vars with defaults:
- MEI_SWING_BREADTH_A default "RSP"
- MEI_SWING_BREADTH_B default "SPY"
- MEI_SWING_CONC_A default "QQQ"
- MEI_SWING_CONC_B default "SPY"
- MEI_SWING_SENT_A default "HYG"
- MEI_SWING_SENT_B default "SHY"
- MEI_SWING_VIX_TICKER default "I:VIX"
- MEI_SWING_VOL_ETF default "VXX"
- MEI_SWING_LOOKBACK default 60
- MEI_SWING_PCTL_LOOKBACK default 20

---

## Task 1 — Define Swing panel specs + computed metrics (still mocked in tests)
### Goal
Create 4 Swing panels using the above proxies, computed from daily close series:
- Breadth Participation (RSP/SPY)
- Concentration Tilt (QQQ/SPY)
- Risk Sentiment (HYG/SHY)
- Volatility Term Structure Proxy (VXX/VIX)

### Implementation requirements
- In backend/main.py swing builder:
  - Fetch daily rows using market_data.client (Polygon) for required tickers.
  - Align series by date intersection (important):
    - Build dict date->close per ticker
    - Intersect dates
    - Compute ratio series only on common dates
  - For each panel compute:
    - latest value (ratio or spread)
    - rolling_percentile(series, MEI_SWING_PCTL_LOOKBACK)
    - regime via classify_regime
    - trend_slope(series[-MEI_SWING_LOOKBACK:])
    - trend_direction from slope sign
  - Raw metrics keys MUST exist even if None:
    - "latest"
    - "percentile_lookback"
    - "regime"
    - "trend_slope"
    - "trend_direction"
    - add "source_tickers" as a string value (e.g. "RSP/SPY") (unit "")
  - Status rules:
    - ok if all needed series exist and sufficient history
    - partial if missing series or insufficient history
    - error only on unexpected exceptions (should trigger fallback)
  - Generate interpretation via generate_interpretation(tab_name="swing", panel=panel_dict)
- Keep schema unchanged.

### Tests (offline)
- Create backend/tests/test_swing_panels_integration.py
  - Monkeypatch market_data.client.get_daily_ohlc (or specific get calls) to return deterministic fixture rows for each ticker.
  - Call get_swing()
  - Assert:
    - schema unchanged
    - panels >= 4
    - each panel has required keys and raw_metrics keys
    - statuses in {"ok","partial","error"}
    - no banned phrases in context/interpretation/why_toggle
- Run pytest -q. Stop and fix before Task 2.

---

## Task 2 — Add fixtures + provider parsing coverage for new tickers
### Goal
Ensure provider parsing + cache logic supports the new ETF tickers in a deterministic way.

### Implementation requirements
- Add fixtures for Polygon daily aggs JSON for:
  - RSP, QQQ, HYG, SHY, VXX (and optional SPY if needed)
- Extend backend/tests/test_market_data_providers.py:
  - ensure polygon_provider parses generic tickers consistently
- Ensure cache keying includes ticker and date range.

### Tests
- pytest -q must pass.

---

## Task 3 — Swing summary + conditional_sensitivity uses new panels (already exists, ensure meaningful)
### Goal
Ensure the tab-level summary/conditional_sensitivity for swing reflects:
- regime counts
- trend counts
- tension counts
- and includes at least one line that references participation/concentration/sentiment/vol (descriptive)

### Implementation requirements
- Update swing summary synthesis (where summary is built) to include one additional descriptive line like:
  - "Swing proxies cover breadth (RSP/SPY), concentration (QQQ/SPY), credit risk appetite (HYG/SHY), and volatility conditions."
- Keep guard_language compliance.

### Tests
- Extend existing summary tests to assert swing summary includes:
  - "Overview:"
  - "Regimes:"
  - "Trends:"
  - and the new descriptive coverage line (exact prefix you choose)
- pytest -q must pass.

---

## Task 4 — Persistence + fallback verification for swing with provider failure
### Goal
Prove swing endpoint also serves last-good snapshot when provider fails.

### Implementation requirements
- Extend backend/tests/test_last_good_fallback.py:
  - Seed a good swing snapshot by calling get_swing() with mocked good data
  - Then monkeypatch urlopen (or polygon provider call) to raise
  - Call /api/swing handler and assert it returns last-good payload
  - Assert audit_log includes build_failed + served_last_good for tab="swing"

### Acceptance criteria for Milestone 8
- /api/swing populated with >= 4 real computed panels (proxies)
- All text guardrailed (no banned phrases)
- Deterministic tests pass and do not hit network
- Persistence + fallback works for swing
- pytest -q passes at end

## Execution instruction to Codex
Implement Tasks 1–4 in order.
After each task, run: `cd backend && source .venv/bin/activate && pytest -q`
Stop and fix failures before moving to the next task.
Return:
- list of files changed
- pytest output
- sample /api/swing payload panels (truncated)