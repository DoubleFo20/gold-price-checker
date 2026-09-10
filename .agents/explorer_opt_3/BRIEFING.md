# BRIEFING — 2026-09-10T04:57:40Z

## Mission
Investigate R3: Eliminating slow/distorted Yahoo Finance calls from /api/historical, serving fast Thai gold data (<100ms) from price_cache or live market baseline, and fixing Admin 7-day chart rendering.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigator, synthesizer
- Working directory: d:\xampp\htdocs\gold-price-checker\.agents\explorer_opt_3
- Original parent: a0b2a93e-c5e3-4950-9ca4-725e4366883a
- Milestone: M-OPT3 (Admin Chart Optimization & Real Baseline Data)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Eliminate slow/distorted Yahoo Finance calls from /api/historical
- Serve fast Thai gold data (<100ms) from price_cache or live market baseline
- Fix Admin 7-day chart rendering (no dense empty grid lines, proper labels)
- Write full report to .agents/explorer_opt_3/report.md and handoff.md

## Current Parent
- Conversation ID: a0b2a93e-c5e3-4950-9ca4-725e4366883a
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `api/routes/prices.py` (lines 92-128: `api_historical` route and cache logic)
  - `api/services/historical.py` (`build_series_with_world_from_yfinance`, `build_series_from_db`, `build_historical_gold_data_free`)
  - `api/sql/goldapidb.sql` (`price_cache` table schema with unique date index)
  - `admin/js/admin.js` (lines 229-305: `loadDashChart`, Chart.js configuration)
  - `admin/index.html` (lines 135-141: `.chart-card`, `#dash-chart` canvas)
  - `admin/css/admin.css` (line 346: `.chart-card canvas` padding issue)
  - `js/script.js` (lines 1270-1340: `loadHistoricalCharts` consuming `/api/historical?days=365`)
  - `tests/e2e/test_tier2_boundaries.py` (line 691: `test_b14_prices_with_invalid_range_param`)
- **Key findings**:
  1. `api_historical()` calls `build_series_with_world_from_yfinance()` which synchronously invokes `yf.Ticker("GLD").history()`, taking 4.38s locally and 10-15s on cloud/Render, or times out.
  2. Data distortion: GLD is an ETF traded on US hours with weekend gaps, shifted by arbitrary basis; furthermore line 84 had a bug multiplying `values_usd` by 10 (`v / factor * 10.0`), distorting spot price to ~$25,000!
  3. Fallback generator in `historical.py` artificially started prices at -12% (`current_thb * 0.88`), creating a fake 5,000 THB spike over 7 days.
  4. Admin 7-day chart distortion caused by missing `maxTicksLimit: 5` and `grace: '8%'` on y-axis (causing 15-25 dense horizontal grid lines when prices are close), vertical grid lines enabled on x-axis, raw ISO date string collision, and CSS padding on the canvas element itself.
  5. Fast solution: `get_historical_gold_data(days)` querying `price_cache` or a clean daily baseline anchored on `bar_sell` with 50-THB increments. Execution time is < 1ms cached, 1-5ms DB, < 1ms baseline.
- **Unexplored areas**: None, all 5 targets fully analyzed.

## Key Decisions Made
- Fully documented the root causes, timing metrics, and architectural fixes.
- Prepared comprehensive `report.md` with complete code diffs for backend and frontend.

## Artifact Index
- report.md — comprehensive findings & implementation plan
- handoff.md — 5-component handoff report
- progress.md — liveness heartbeat
