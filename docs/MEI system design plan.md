Below is an implementation-oriented system design plan that directly translates the MEI draft into buildable architecture and logic, without adding prediction, signals, or scope.

---

## **1️⃣ System Architecture Overview**

### **Core components (MVP, solo builder)**

1. **Web UI (2 tabs)**  
* Intraday Tab (4 panels) \+ Intraday Conditional Sensitivity \+ Intraday Summary  
* Swing Tab (5 panels) \+ Swing Conditional Sensitivity \+ Swing Summary  
* Each panel renders: **A) Raw metrics → B) Context → C) Neutral interpretation → D) Optional “Why this matters” toggle**  
2. **Backend API (monolith)**  
* Fetches market/macro/sentiment data (via providers)  
* Computes derived metrics (percentiles, trends, correlations, regimes)  
* Runs the **Interpretation Engine** (rule-based, language-disciplined)  
* Stores snapshots \+ computed states \+ generated text blocks  
3. **Data ingestion layer**  
* Simple pull-based fetchers per provider (REST)  
* Lightweight caching (per symbol \+ timeframe \+ endpoint)  
* Optional: end-of-day “swing snapshot” job  
4. **Processing layer**  
* Normalization (units, timezones, trading calendar alignment)  
* Computation library (deterministic functions)  
* State registry (per metric: raw → normalized → derived → state labels)  
5. **Interpretation engine**  
* Rule templates per panel \+ global discipline guardrails  
* Conflict detection \+ weighted force summary synthesis  
* Output \= structured interpretation blocks \+ final summary block per tab  
6. **Storage**  
* **SQLite** (MVP): snapshots, computed metrics, states, interpretations, audit logs  
* Optional file store (Parquet/CSV) only if you want cheap historical bulk caching

### **Component interaction (request flow)**

**UI → Backend**

* `GET /api/intraday` → backend fetches latest intraday inputs (or uses cache), computes intraday panel metrics/states, runs interpretation engine, returns panel blocks \+ summary  
* `GET /api/swing` → uses daily/periodic cached swing dataset, computes swing panel metrics/states, runs interpretation engine, returns blocks \+ summary

### **Update cadence (per draft intent)**

* **Intraday tab:** refresh frequently (structure-dominant, macro-aware)  
* **Swing tab:** refresh slower (macro-dominant, structure-confirmed)

### **Modular separation (tabs and panels)**

* Code structure: `modules/intraday/{panel1..4}.py`, `modules/swing/{panel1..5}.py`  
* Shared libs: `lib/data_providers.py`, `lib/normalize.py`, `lib/compute.py`, `lib/interpret.py`, `lib/language_guard.py`  
* Each panel is self-contained: **inputs → computations → states → interpretation block**

---

## **2️⃣ Data Requirements (per metric in the draft)**

**Notes**

* “Free” options are realistic but sometimes less reliable; MVP can start free and swap to paid.  
* Timezones: normalize to **US/Eastern** for market sessions; store UTC timestamps.

### **Intraday Tab — Panel 1: Intraday Volatility State**

1. **Current range percentile (30–60d lookback)**  
* Data: Index intraday high/low (or minute bars)  
* Frequency: 1–5 min bars (or compute from day’s developing H/L)  
* Free: Stooq (daily only), Yahoo (limited intraday), MarketData.app (limited)  
* Paid: Polygon.io, Alpaca, Tiingo, Tradier  
* Normalization: range \= (high-low)/prev\_close (or /open; choose one consistently)  
* Lookback: 30–60 prior trading days  
* Storage: store daily realized ranges \+ today developing range in SQLite  
2. **VIX % change from open**  
* Data: VIX intraday last \+ session open  
* Frequency: 1–5 min  
* Free: often delayed/limited; some providers offer delayed CBOE-derived  
* Paid: Polygon.io (indices), Cboe data vendors, Nasdaq Data Link (varies)  
* Normalization: `%chg = (last - open)/open`  
* Lookback: none required for %chg; optional for percentile context  
* Storage: store open \+ last snapshots  
3. **Gap percentile (open vs prior close)**  
* Data: Index open \+ prior close (daily)  
* Frequency: once per day (at open), update stable afterwards  
* Free: Stooq daily, Yahoo daily  
* Paid: Polygon/Tiingo  
* Normalization: gap \= (open \- prev\_close)/prev\_close (absolute for “gap size” percentile)  
* Lookback: 30–60 trading days  
* Storage: daily gaps table

### **Intraday Tab — Panel 2: Participation & Structure**

4. **Advance/Decline ratio**  
* Data: advancers/decliners for an exchange (NYSE) or index universe  
* Frequency: 1–5 min  
* Free: limited; some public endpoints exist but unreliable  
* Paid: Polygon (market breadth), Intrinio, Nasdaq/ICE feeds  
* Normalization: `ADR = advancers / max(decliners,1)`; clamp extreme values  
* Lookback: optional percentiles 20–60d (same session time-of-day is “nice to have” but not required for MVP)  
* Storage: intraday ADR snapshots \+ daily close ADR  
5. **% index weight driving move (concentration proxy)**  
* MVP proxy (practical): contribution of top N constituents or top N holdings of a liquid ETF proxy (e.g., SPY/QQQ)  
* Data: constituent returns \+ weights  
* Frequency: 5–15 min (weights daily; returns intraday)  
* Free: ETF holdings are public (daily-ish) but scraping is brittle  
* Paid: IEX Cloud (constituents), Polygon reference data, Intrinio, FactSet/Bloomberg (expensive)  
* Normalization: compute contribution shares (see §3)  
* Lookback: 20–60d percentiles  
* Storage: daily weights snapshot \+ intraday constituent returns (or just top N)  
6. **Volume vs 20-day average**  
* Data: index/ETF volume intraday cumulative vs historical average daily volume  
* Frequency: 1–5 min cumulative volume  
* Free: Yahoo daily volume (intraday less reliable)  
* Paid: Polygon/Tiingo/Alpaca  
* Normalization: `vol_ratio = cum_volume_today / avg_volume_20d`  
* Lookback: 20 trading days  
* Storage: daily volumes \+ today cum volume

### **Intraday Tab — Panel 3: Cross-Asset Drivers**

7. **10Y yield change (daily)**  
* Data: 10Y yield (e.g., DGS10 from FRED is daily)  
* Frequency: daily (intraday yield is harder; MVP can use daily change)  
* Free: FRED (daily)  
* Paid: Refinitiv/Bloomberg for intraday  
* Normalization: basis points change: `(y_today - y_prev)*100`  
* Lookback: 60–252d for percentiles if desired  
* Storage: daily time series  
8. **DXY change (daily)**  
* Data: DXY (or UUP ETF as proxy)  
* Frequency: daily (intraday optional)  
* Free: Stooq (daily), Yahoo (UUP)  
* Paid: Polygon/FX feeds  
* Normalization: `%chg` or absolute  
* Lookback: 60–252d  
* Storage: daily time series  
9. **Oil change (daily)**  
* Data: WTI (CL) or USO ETF proxy  
* Frequency: daily  
* Free: Stooq/Yahoo (USO), EIA series (often delayed)  
* Paid: Polygon/futures feed  
* Normalization: `%chg`  
* Lookback: 60–252d  
* Storage: daily time series

### **Intraday Tab — Panel 4: Event & Short-Term Positioning Context**

10. **Implied move for next major earnings (if relevant)**  
* Data: option-implied move for specific ticker(s)  
* Frequency: daily/intraday near event  
* Free: limited  
* Paid: Tradier, Intrinio, ORATS, ivolatility  
* Normalization: `implied_move_% = ATM_straddle_price / spot`  
* Lookback: 60–252d percentile optional  
* Storage: per-event snapshot  
11. **Days to major macro event (CPI/Fed/etc.)**  
* Data: economic calendar  
* Frequency: daily  
* Free: many calendars (scrape/API); quality varies  
* Paid: Econoday, Bloomberg  
* Normalization: integer days  
* Lookback: none  
* Storage: events table  
12. **Optional: dealer gamma regime**  
* Data: dealer gamma estimates  
* Frequency: daily/intraday  
* Free: rare  
* Paid: SpotGamma, SqueezeMetrics, Tier1Alpha, etc.  
* Normalization: categorical (positive/negative/neutral) \+ percentile if vendor provides  
* Storage: daily snapshot \+ source attribution

---

### **Swing Tab — Panel 1: Volatility Regime**

13. **VIX percentile (6–12m)**  
* Data: VIX daily close  
* Frequency: daily  
* Free: Stooq daily  
* Paid: Polygon/CBOE vendors  
* Normalization: percentile on 126–252 trading days  
* Storage: daily VIX  
14. **ATR percentile (50-day)**  
* Data: index/ETF daily OHLC  
* Frequency: daily  
* Free: Stooq/Yahoo  
* Paid: Polygon/Tiingo  
* Normalization: ATR(14) or ATR(20) then percentile over 50d (see §3)  
* Lookback: 50 trading days (plus ATR warmup)  
* Storage: daily OHLC \+ computed ATR  
15. **Volatility trend (expanding/contracting)**  
* Data: VIX and/or ATR series  
* Frequency: daily  
* Normalization: slope over lookback (e.g., 20d) \+ label  
* Storage: derived

### **Swing Tab — Panel 2: Financial Conditions Core**

16. **10Y yield 3-month change**  
* Data: 10Y yield daily  
* Frequency: daily  
* Free: FRED  
* Normalization: `Δ3m = y_t - y_{t-63}`  
* Lookback: 63 trading days  
* Storage: daily yields  
17. **Real yield trend (if available)**  
* Data: 10Y TIPS yield (FRED series like DFII10)  
* Frequency: daily  
* Free: FRED  
* Normalization: trend label from slope over 20–60d  
* Storage: daily  
18. **DXY 3-month trend**  
* Data: DXY or UUP  
* Frequency: daily  
* Normalization: slope or MA change over \~63d  
* Storage: daily  
19. **Credit spread direction (tightening/widening)**  
* Data: credit spread series (e.g., ICE BofA option-adjusted spreads via FRED)  
* Frequency: daily  
* Free: FRED OAS series  
* Paid: Bloomberg/ICE direct  
* Normalization: slope over 20–60d \+ direction label  
* Storage: daily

### **Swing Tab — Panel 3: Equity Structure Confirmation**

20. **% stocks above 50-day MA**  
* Data: constituent daily closes \+ 50d MA  
* Frequency: daily  
* Free: hard to do robustly without a constituent data service  
* Paid: IEX Cloud/Polygon reference \+ prices, Intrinio  
* MVP alternative: use breadth proxy ETFs or existing breadth endpoints (if provider supports)  
* Normalization: percent (0–100)  
* Lookback: 252d for percentile optional  
* Storage: daily per-constituent close (or computed breadth only)  
21. **Index concentration ratio (top 5 weight)**  
* Data: top weights of the index/ETF holdings  
* Frequency: daily/weekly (weights)  
* Free: ETF holdings pages (scrape) — acceptable for internal MVP  
* Paid: index data vendors  
* Normalization: `conc_top5 = sum(weights_top5)`  
* Lookback: 6–12m history if available  
* Storage: weights snapshots  
22. **Sector rotation (cyclical vs defensive relative strength)**  
* Data: sector ETFs daily prices (e.g., XLY/XLP, XLK/XLU, XLF/XLU)  
* Frequency: daily  
* Free: Yahoo/Stooq  
* Normalization: ratio returns and trend (see §3)  
* Lookback: 63–126d  
* Storage: daily ETF closes

### **Swing Tab — Panel 4: Sentiment & Positioning**

23. **Put/Call percentile (3–6m)**  
* Data: CBOE total put/call (or equity-only)  
* Frequency: daily  
* Free: some public series exist but inconsistent  
* Paid: CBOE data vendors, Quandl/Nasdaq Data Link products  
* Normalization: percentile over 63–126d  
* Storage: daily  
24. **Survey sentiment percentile**  
* Data: AAII bulls/bears, Investors Intelligence (paid), Sentix (paid)  
* Frequency: weekly  
* Free: AAII provides weekly data (access method varies)  
* Normalization: percentile over 1–3y weekly history  
* Storage: weekly series  
25. **Volatility skew**  
* Data: SPX skew index or 25-delta risk reversal proxy  
* Frequency: daily  
* Free: limited  
* Paid: options analytics vendors  
* Normalization: percentile over 6–12m  
* Storage: daily

### **Swing Tab — Panel 5: Catalyst & Event Context**

26. **Days to major macro event**  
* Same as intraday \#11  
27. **Implied move for major index-heavy earnings**  
* Same method as intraday \#10 but for selected “index-heavy” names (config list)

---

## **3️⃣ Computation & Logic Layer (precise, deterministic)**

### **3.1 Percentile calculations**

For any metric series (x) and lookback window (L):

**Rolling percentile rank (empirical CDF):**  
\[  
p\_t \= \\frac{1}{L}\\sum\_{i=1}^{L} \\mathbf{1}(x\_{t-i} \\le x\_t)  
\]  
Return as 0–100.

**Implementation details**

* Use a rolling window over **prior observations** (exclude current if you want strict comparability; include current for simplicity—pick one and document it).  
* Handle missing data: require minimum (L\_{min}) (e.g., 80% of L) else “insufficient history”.

### **3.2 Regime classification (generic)**

Convert percentiles into categorical states:

* **Low:** (p \< 30\)  
* **Mid:** (30 \\le p \\le 70\)  
* **High:** (p \> 70\)

For “event-driven” detection (intraday):

* flag if any of:  
  * Range percentile \> 80  
  * |VIX % change from open| \> threshold (e.g., 2–3% configurable)  
  * Gap percentile \> 80

### **3.3 Correlation detection (cross-asset driver linkage)**

Use rolling correlation between **intraday index returns** and **cross-asset returns**.

For aligned return series (r^{idx}*t), (r^{asset}t) over window (W) (e.g., last 60–120 minutes):*  
*\[*  
*\\rho\_t \= corr(r^{idx}{t-W+1:t}, r^{asset}*{t-W+1:t})  
\]

**State labels**

* “Low linkage”: (|\\rho| \< 0.25)  
* “Moderate linkage”: (0.25 \\le |\\rho| \< 0.5)  
* “High linkage”: (|\\rho| \\ge 0.5)

**Driver hinting (still neutral)**

* If yields show high linkage and DXY/oil do not → “rate-linked”  
* If DXY shows high linkage → “dollar-linked”  
* If oil shows high linkage → “inflation-sensitive”  
* If none show linkage → “internally generated” (per draft wording)

### **3.4 Trend detection (swing)**

Use linear slope on log prices (robust and scale-free) over lookback (N) (e.g., 20 or 63 days).

Let (y\_t \= \\log(price\_t)), fit (y \= a \+ bt). Trend strength \= (b).

**Trend state**

* “Uptrend”: (b \> \+\\epsilon)  
* “Downtrend”: (b \< \-\\epsilon)  
* “Flat”: (|b| \\le \\epsilon)

Choose (\\epsilon) small (e.g., (1e^{-4})) or scale by volatility.

### **3.5 Volatility compression / expansion (intraday \+ swing)**

**Swing**

* Compute ATR (e.g., ATR(14)):  
  * True Range: (TR\_t \= \\max(H\_t-L\_t, |H\_t-C\_{t-1}|, |L\_t-C\_{t-1}|))  
  * ATR: EMA/SMA of TR over 14  
* ATR percentile over 50d \= compression/expansion context  
* Vol trend: slope of VIX (or ATR) over 20d

**Intraday**

* Use current developing range vs historical daily range distribution:  
  * Range today: (R\_t \= (H\_{today}-L\_{today})/C\_{prev})  
  * Range percentile over 30–60d  
* Compression: range percentile \< 30  
* Expansion: range percentile \> 70  
* Event-driven overlay: see §3.2

### **3.6 Concentration proxy (participation integrity)**

If you have weights (w\_i) and returns (r\_i) for constituents (i), index return approx:  
\[  
r^{idx} \\approx \\sum\_i w\_i r\_i  
\]  
Contribution share for top N:  
\[  
share\_{topN} \= \\frac{\\sum\_{i \\in topN} w\_i r\_i}{\\sum\_{all} |w\_i r\_i| \+ \\delta}  
\]  
(use absolute denom to avoid sign cancellation; (\\delta) small)

State examples:

* “Broad”: share\_topN \< 0.45  
* “Narrow”: share\_topN \> 0.65  
  (thresholds configurable)

### **3.7 Breadth (% above 50d MA)**

For universe (U):  
\[  
breadth\_t \= \\frac{1}{|U|}\\sum\_{i \\in U} \\mathbf{1}(P\_{i,t} \> MA\_{50,i,t})  
\]

### **3.8 Sector rotation (cyclical vs defensive RS)**

Pick ratio series:

* (RS\_t \= \\frac{Price\_{cyclical}}{Price\_{defensive}})  
  Compute trend on (\\log(RS\_t)) over 20–63d and label as “cyclical leadership strengthening/weakening/flat” (neutral phrasing).

---

## **4️⃣ Interpretation Engine Design (rule-based, neutral, disciplined)**

### **4.1 Engine outputs (structured)**

For each panel:

* **Raw Metrics:** numeric values \+ deltas  
* **Context:** percentiles \+ regime labels  
* **Neutral Interpretation:** 1–2 sentences using “historically associated with…”  
* **Optional Toggle Text:** “why traders care / concept” (static content per metric cluster)

Per tab:

* Conditional Sensitivity section (Option B framing)  
* Final Summary (force-weighted integration; 3–4 sentences intraday, 4 sentences swing)

### **4.2 Language Discipline Rulebook enforcement (hard guardrails)**

Implement a **language guard** that runs on every generated sentence:

* Block/replace disallowed tokens/phrases: “will”, “going to”, “crash”, “rally”, “buy”, “sell”, “target”, “guarantee”, etc.  
* Require at least one of these framings per interpretation block:  
  * “historically associated with”  
  * “tends to coincide with”  
  * “has often been observed alongside”  
* Force conditional phrasing for sensitivities:  
  * “If X were to occur…”  
  * “Under current conditions…”  
  * “Given \[state\]…”

If violations occur:

* Return a safe fallback: “Current readings are best treated as context; no directional implication is inferred.”

### **4.3 Interpretation templates (panel-level)**

Use deterministic templates with slot filling \+ state-based clauses.

**Template example (Volatility state, intraday)**

* Context sentence:  
  * “Today’s realized range sits in the {range\_pct}th percentile versus the last {L} sessions, with VIX {vix\_chg\_pct}% from the open and a gap size in the {gap\_pct}th percentile.”  
* Neutral interpretation:  
  * “Historically, higher realized-range percentiles are associated with faster information repricing and less stable intraday pacing, while lower percentiles are associated with more contained movement.”

**Template example (Participation & structure)**

* “Breadth (A/D {adr}) and concentration ({share\_topN\_label}) currently indicate {structure\_state} participation. Historically, narrow participation is associated with more fragile index-level moves than broad participation, without implying direction.”

**Template example (Cross-asset drivers with correlation)**

* “Rolling linkage over the last {W} minutes is {rate\_linkage\_state} to rates, {dxy\_linkage\_state} to USD, and {oil\_linkage\_state} to oil. Historically, stronger linkage suggests the tape is more sensitive to that macro driver’s incremental changes.”

### **4.4 Sensitivity framing templates (Option B only)**

Generate 1–3 bullets per tab.

**Mode A (state) \+ Option B (conditional) structure**

* “Under current {vol\_state} conditions…”  
* “Given {macro\_state} financial conditions…”  
* “If {event} were to deliver a material surprise relative to expectations…”  
* “The market has historically been more sensitive to {driver} changes when {condition}.”

No direction; only reaction sensitivity.

### **4.5 Weighted force summary synthesis (non-predictive)**

Define fixed weights per panel (config), sentiment capped:

**Intraday weights (example)**

* Panel 1 Vol state: 0.40  
* Panel 2 Participation: 0.30  
* Panel 3 Cross-asset: 0.20  
* Panel 4 Event/positioning: 0.10

**Swing weights (example)**

* Financial conditions core: 0.40  
* Vol regime: 0.25  
* Equity structure: 0.20  
* Sentiment/positioning: 0.10 (cap)  
* Catalyst context: 0.05

**Dominant force selection**

* Compute each panel “force score” \= weight × severity  
* Severity example: distance from neutral percentile band:  
  * (sev \= \\max(0, |p-50|-20)/30) clipped 0–1  
* Dominant force \= highest force score; secondary \= next highest (if above a small threshold)

**Summary template (intraday)**

1. Dominant force statement (from dominant panel template)  
2. Secondary modifier statement  
3. Sensitivity condition (only if event/vol flags present)  
4. Optional conflict sentence (if needed)

### **4.6 Conflict detection logic (acknowledge, don’t resolve)**

Create conflict rules between panel states, e.g.:

* Vol expansionary \+ breadth weak \+ concentration narrow → “fast tape, fragile participation”  
* Macro tightening \+ equity breadth improving → “macro pressure not uniformly reflected internally”  
* Sentiment stretched optimistic \+ vol compressed → “reduced margin for surprise without implying direction”

If conflict triggers:

* Add 1 sentence: “Signals are currently mixed across {A} and {B}; historically this is associated with less stable inference.”

---

## **5️⃣ Sentiment Integration Design**

### **5.1 How sentiment metrics are computed (deterministic)**

* Put/Call percentile: rolling percentile over 63–126 trading days  
* Survey sentiment percentile: rolling percentile over 52–156 weeks  
* Skew percentile: rolling percentile over 126–252 trading days

Convert each to state: Low/Mid/High \+ “stretched” if \>80 or \<20.

### **5.2 How sentiment modifies structural interpretation**

Sentiment never becomes the “dominant force.” It only attaches as:

* **Asymmetry / positioning pressure modifier**  
* Only referenced after macro/structure statements

Example modifier clause:

* “Positioning appears {stretched\_state}; historically, this is associated with altered surprise sensitivity (asymmetry) rather than a directional forecast.”

### **5.3 Prevent sentiment from dominating**

* Hard weight cap in summary synthesis (e.g., 0.10 swing)  
* Hard ordering rule: sentiment cannot be sentence \#1 in any summary  
* If sentiment severity is extreme, allow at most one additional sentence, still framed as “margin for surprise,” not “too bullish/bearish.”

### **5.4 Framing asymmetry without prediction**

Allowed patterns:

* “Optimistic positioning reduces margin for positive surprise.”  
* “Stretched hedging demand has historically coincided with larger reactions to incremental news.”  
  Disallowed:  
* “This means market will reverse.”

---

## **6️⃣ UI & Panel Layout Blueprint (structural)**

### **Intraday Tab (4 panels)**

**Top row**

1. **Panel 1: Intraday Volatility State**  
   * Raw metrics (range pct, VIX %chg, gap pct)  
   * Context labels (compressed/normal/expansionary/event-driven)  
   * Interpretation (1–2 sentences)  
   * Toggle: “why range percentiles matter”  
2. **Panel 2: Participation & Structure**  
   * A/D ratio, concentration proxy, volume ratio  
   * Interpretation \+ toggle

**Bottom row**  
3\) **Panel 3: Cross-Asset Drivers**

* 10Y bp change, DXY %chg, oil %chg  
* Optional “linkage meter” text (low/moderate/high correlation)  
* Interpretation \+ toggle  
4. **Panel 4: Event & Short-Term Positioning Context**  
   * Implied move (if relevant), days to macro event, optional gamma regime  
   * Interpretation \+ toggle

**Below panels**

* **Intraday Conditional Sensitivity Section** (collapsed by default; expands)  
* **Intraday Summary** (always visible; 3–4 sentences max)

### **Swing Tab (5 panels)**

**Top row (3 panels)**

1. Volatility Regime  
2. Financial Conditions Core (center, visually primary)  
3. Equity Structure Confirmation

**Bottom row (2 panels)**  
4\) Sentiment & Positioning  
5\) Catalyst & Event Context

**Below panels**

* **Swing Conditional Sensitivity Section** (collapsed by default)  
* **Swing Summary** (always visible; 4 sentences max)

### **Minimalist design recommendations**

* Favor text labels \+ small numeric chips (percentiles, deltas) over charts for MVP  
* Use consistent “State badges” (Low/Mid/High; Tightening/Easing; Compressed/Expanded)  
* Educational toggle is per-panel, off by default (pre-written static text)

---

## **7️⃣ Update Cadence & Automation**

### **Intraday refresh frequency**

* **Every 1–5 minutes** during market hours  
* Add “manual refresh” button  
* Cache provider calls (e.g., 30–60s TTL per endpoint)

### **Swing refresh frequency**

* **Once daily** after market close (or pre-market), plus weekly sentiment updates  
* Optional: mid-day refresh for rates/DXY/oil if you want

### **Event-driven triggers**

* At market open: compute gap \+ open baselines  
* At scheduled macro events: refresh event context \+ mark “event window”  
* If VIX %chg crosses threshold or range percentile jumps: force refresh \+ log “event-driven flag”

### **Data validation safeguards**

* Range checks (e.g., percentiles 0–100)  
* Staleness checks (timestamp freshness)  
* Missing critical inputs → degrade gracefully:  
  * Still render panel with “insufficient data” state and neutral fallback text  
* Provider mismatch detection (e.g., sudden 10Y yield spike beyond plausible bps range)

### **Logging & error handling**

* Structured logs per job/run:  
  * fetch success/fail, latency, rows ingested, derived metrics computed  
* Error categories: provider error, parse error, insufficient history, computation error  
* Store last-good snapshot per tab; UI can show “last updated” timestamp

---

## **8️⃣ Scalability Plan (Future-Proofing without bloat)**

### **Modular metric registry (prevents bloat)**

Use a **metric registry** (YAML/JSON) defining for each metric:

* id, panel, timeframe (intraday/swing)  
* data source adapter  
* frequency \+ lookback window  
* normalization function  
* state thresholds  
* interpretation template ids

This lets you add metrics by configuration \+ one compute function, not by rewriting panels.

### **Add metrics later (safe process)**

1. Add metric to registry with explicit scope (which panel, which summary weight impact)  
2. Implement deterministic compute \+ state mapping  
3. Add interpretation template \+ language guard tests  
4. Run regression checks (see below) before enabling

### **Maintain interpretive discipline over time**

* **Locked vocabulary list** \+ disallowed phrase list (unit-tested)  
* Golden test cases: fixed input states → expected neutral outputs  
* Summary ordering rules enforced (dominant force first; sentiment never first)

### **When to scale architecture (only if needed)**

* SQLite → Postgres when you want multi-user or high write concurrency  
* Add background job runner (Celery/RQ) only if intraday fetch/computation becomes slow  
* Add a time-series store only if you start storing large intraday histories (not required for MVP)

---

If you want, I can also provide (a) a concrete SQLite schema (tables \+ key fields) and (b) example API endpoints/payloads for `GET /intraday` and `GET /swing` that return panel blocks exactly in the A/B/C/D structure from the draft.

