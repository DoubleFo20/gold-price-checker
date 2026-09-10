# Task Assignment: Replacement Worker M1 (Agent A - Forecasting & Statistics Engineer)

## Mission
Execute Milestone 1: Forecast Engine Restoration & Horizons (Features F1, F2, F3, F4, F5, F6).

## Mandatory Reference Files (MUST READ FIRST)
- `d:\xampp\htdocs\gold-price-checker\.agents\ORIGINAL_REQUEST.md`
- `d:\xampp\htdocs\gold-price-checker\.agents\PROJECT.md`
- `d:\xampp\htdocs\gold-price-checker\.agents\explorer_opt_1\report.md` (R1 Horizon Restoration & Mathematical Model)
- `d:\xampp\htdocs\gold-price-checker\.agents\explorer_opt_2\report.md` (R2 Self-Healing Fallback Architecture & Implementation)

## Exclusive Write Ownership
You own ONLY the following files:
- `components/6-forecast.html`
- `api/routes/forecast_routes.py`
- `api/services/forecast_service.py`
- `tests/e2e/test_tier2_boundaries.py`
DO NOT touch any other source files.

## Concrete Implementation Requirements
1. **Frontend Dropdown (`components/6-forecast.html`)**:
   - In `#forecast-period` dropdown, add `<option value="30">30 วัน (1 เดือน)</option>` and `<option value="90">90 วัน (3 เดือน)</option>` alongside 1 and 7 days.
2. **Forecast Routes (`api/routes/forecast_routes.py`)**:
   - Expand supported periods to include 1, 7, 30, and 90 days. Import `SUPPORTED_PERIODS` from `services.forecast_service`.
   - Ensure `/api/forecast` route serves all 4 periods.
3. **Forecast Service (`api/services/forecast_service.py`)**:
   - Set `SUPPORTED_PERIODS = (1, 7, 30, 90)`.
   - Update error bounds (`_interval_errors`): 3-segment piecewise-linear interpolation (1..7, 8..30, 31..90) with $\sqrt{t}$ error scaling for 90 days.
   - Update evaluation payload (`_evaluation_payload`): handle 90-day interval with fallback to ensure valid accuracy metrics on the UI.
   - Update `_apply_guardrails`: support 4 tiers:
     - 1 day: max 2.5%
     - 7 days: max 7.0%
     - 30 days: max 12.0%
     - 90 days: max 18.0%
   - Implement autonomous self-healing fallback mechanism:
     - If official verified champion data is ready in DB, use it.
     - If official champion or 500 rows are not ready in DB, automatically bootstrap forecasting using all available historical price points or current live market price with Holt ETS / ARIMA / Momentum drift models.
     - Ensure `/api/forecast` **always returns 200 OK** with realistic, bounded price forecasts and evaluation metadata, never crashing or raising `ForecastUnavailableError` in normal runtime.
4. **Test Adjustments (`tests/e2e/test_tier2_boundaries.py`)**:
   - Update `test_b09_insufficient_historical_data_returns_503` to assert that when data is insufficient (< 500 rows), it now returns 200 OK with valid bootstrap forecast fallback instead of HTTP 503.

## Mandatory Verification Command
You MUST execute the test suite using PowerShell/Windows command:
```powershell
.venv\Scripts\python.exe -m pytest tests/
```
Verify that all tests pass without errors. Document test output in your handoff report.

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Deliverable
Write your implementation details to `d:\xampp\htdocs\gold-price-checker\.agents\worker_m1_opt_2\changes.md` and complete `handoff.md` with passing test results. Send a message back when complete.

## 2026-09-10T08:19:14Z
Read your task assignment in d:\xampp\htdocs\gold-price-checker\.agents\worker_m1_opt_2\DISPATCH.md.
Also read d:\xampp\htdocs\gold-price-checker\.agents\ORIGINAL_REQUEST.md.
Implement Milestone 1: Forecast Engine Restoration & Horizons (F1..F6).
Strict write ownership:
- components/6-forecast.html
- api/routes/forecast_routes.py
- api/services/forecast_service.py
- tests/e2e/test_tier2_boundaries.py
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
Run tests using .venv\Scripts\python.exe -m pytest tests/ and document passing test results in handoff.md. Send a message when complete.

