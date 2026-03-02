# CURRENT SYSTEM STATE (March 2026)

## Backend (Locked Quant Rules)
- Real data sources:
  - Massive/Polygon for daily OHLC (SPY, VIX proxy ticker, swing proxy tickers)
  - FRED for yield macro series (default DGS10)
- Persistence and resilience:
  - SQLite market cache (`market_cache`)
  - SQLite snapshots + audit logs
  - Last-good snapshot fallback on provider/build failure
- Series depth rules:
  - Target bars: 252
  - Minimum bars: 120
- Percentile method:
  - Rolling percentile excludes current value from reference set
  - If insufficient history, percentile is `None`
- Default lookbacks:
  - Intraday percentile lookback: 126
  - Swing percentile lookback: 252
  - Trend lookback: 126 (current configured default)
- Panel status logic:
  - `ok`: required history available and compute succeeds
  - `partial`: insufficient history for percentile/trend or partial compute path
  - `error`: unexpected compute/provider failure path
- Summary engine:
  - Weighting engine is active
  - Structured summary format includes `Lead`, `Support`, `Mixed`/signal balance, `Scope`, and `Diagnostics`
- Lookback selector support:
  - `GET /api/intraday?lookback=20|60|252`
  - `GET /api/swing?lookback=20|60|252`
  - Invalid lookbacks return HTTP 400 with a clear error message
- Volatility source behavior:
  - VIX index access may be forbidden by provider permissions
  - System uses VIX proxy (`VXX`) fallback and labels it explicitly

## API Payload Notes
- `/api/intraday` and `/api/swing` are computed real-data payloads.
- Additive panel fields may appear and must be treated as non-breaking:
  - `sparkline`
  - `sparkline_times`
  - `window_meta` (when present: series points, target/min bars, lookbacks, percentile mode)
- Lookback metadata (additive):
  - `payload.window_meta.lookback_selected` (when lookback query param is used)
  - `panels[].window_meta.lookback_selected` (when lookback query param is used)
- `/api/market/status` includes per-source diagnostics and additive fields:
  - `provider_rows`, `clean_rows`, `rows_after_intersection`, `rows_used_for_percentile`
  - `last_error`, `label`
  - Current volatility source label is `VIX proxy (VXX)`
- Debug endpoint:
  - `GET /api/debug/percentile_sanity` (read-only)
  - Purpose: percentile distribution sanity diagnostics (extremes and clustering checks) for SPY, VXX, DGS10 at lookbacks 126 and 252

## Frontend
- Dark quant UI is active.
- Chart-dominant layout is active.
- Lightweight Charts v5 is active.
- Focused chart + stats/summary UI state is active.
- Codespaces rule remains: browser hits frontend routes only; frontend proxies to backend internally.
- Lookback selector UI is active (20/60/252) with default selection `60` on first load.

## Open Focus
- Bar-count verification against provider-returned rows and overlap intersections
- Lookback selector (20/60/252)
- Crosshair tooltip and hover value polish
- Comparison overlay support
- Percentile distribution display
