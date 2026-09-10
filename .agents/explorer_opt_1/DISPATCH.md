# Task Assignment: Explorer 1 (Forecasting Horizons & Frontend/Backend Pipeline)

## Mission
Investigate R1: Restoring 30-Day and 90-Day Forecast Horizons across UI and Backend.

## Working Directory
`d:\xampp\htdocs\gold-price-checker\.agents\explorer_opt_1`

## Mandatory Reference Files
- `d:\xampp\htdocs\gold-price-checker\.agents\ORIGINAL_REQUEST.md` (MUST read first)
- `d:\xampp\htdocs\gold-price-checker\.agents\PROJECT.md`

## Specific Scope & Investigation Targets
1. Examine `components/6-forecast.html` and any related JS (`js/forecast.js`, `js/script.js`, etc.) to find the `#forecast-period` dropdown and period handling. Identify how 30-day and 90-day options should be added and handled in the UI and charts.
2. Examine `api/routes/forecast_routes.py` and `api/services/forecast_service.py` to identify where `SUPPORTED_PERIODS` is defined and used.
3. Investigate `_interval_errors` and `_evaluation_payload` in `forecast_service.py` or related modules to determine how 90-day intervals are configured, bounded, and formatted.
4. Check error bounds and validation constraints across 1, 7, 30, and 90 days.
5. Identify any existing tests in `tests/` covering forecast horizons and what test additions or adjustments are needed.

## Deliverable
Write your detailed findings and actionable recommendations to `d:\xampp\htdocs\gold-price-checker\.agents\explorer_opt_1\report.md` and complete with `handoff.md`. Send a brief message back when finished.

## 2026-09-09T21:52:43Z
Read your task assignment in d:\xampp\htdocs\gold-price-checker\.agents\explorer_opt_1\DISPATCH.md.
Also read d:\xampp\htdocs\gold-price-checker\.agents\ORIGINAL_REQUEST.md.
Investigate R1: Restoring 30-Day and 90-Day Forecast Horizons in components/6-forecast.html, api/routes/forecast_routes.py, api/services/forecast_service.py, _interval_errors, _evaluation_payload, and test coverage.
Write your full report to d:\xampp\htdocs\gold-price-checker\.agents\explorer_opt_1\report.md and handoff.md in your working directory. Send a message when complete.

