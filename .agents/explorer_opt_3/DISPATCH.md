# Task Assignment: Explorer 3 (Admin Chart Optimization & Real Baseline Data)

## Mission
Investigate R3: Eliminating slow, distorted Yahoo Finance data fetch from the Admin dashboard chart, serving real Thai gold data in < 100ms, and rendering clean charts.

## Working Directory
`d:\xampp\htdocs\gold-price-checker\.agents\explorer_opt_3`

## Mandatory Reference Files
- `d:\xampp\htdocs\gold-price-checker\.agents\ORIGINAL_REQUEST.md` (MUST read first)
- `d:\xampp\htdocs\gold-price-checker\.agents\PROJECT.md`

## Specific Scope & Investigation Targets
1. Examine `/api/historical` route implementation (in `api/routes/` or similar) and identify where synchronous Yahoo Finance (`yfinance`) calls are made.
2. Check why Yahoo Finance causes 12-second latency and distorted data in the Admin 7-day chart.
3. Investigate how `/api/historical` can immediately serve real Thai gold data from local `price_cache` or a clean daily baseline anchored on live market price (`bar_sell`), responding in < 100ms.
4. Investigate the Admin dashboard frontend (`admin/` or `components/` or `js/admin.js`, chart rendering libraries) to see why the 7-day chart was distorted (dense empty grid lines, label formatting issues).
5. Identify required changes to ensure crisp, realistic gold prices with proper labels and fast response times.

## Deliverable
Write your detailed findings, latency analysis, and concrete implementation plan to `d:\xampp\htdocs\gold-price-checker\.agents\explorer_opt_3\report.md` and complete with `handoff.md`. Send a brief message back when finished.
