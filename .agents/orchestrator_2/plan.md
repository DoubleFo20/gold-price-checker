# Execution Plan — Forecast Engine Restoration & Admin Chart Optimization

## Objectives
1. R1: Restore 30-Day and 90-Day Forecast Horizons in UI (`components/6-forecast.html`) and Backend (`forecast_routes.py`, `forecast_service.py`, `_interval_errors`, `_evaluation_payload`).
2. R2: Self-Healing Production Fallback for `/api/forecast` to eliminate "ข้อมูลจริงยังไม่พร้อมสำหรับการพยากรณ์" (always 200 OK, bounded predictions, bootstrap via available data or live price with Holt ETS / ARIMA / Momentum drift models).
3. R3: Remove synchronous Yahoo Finance (`yfinance`) blocking calls from `/api/historical`, serve real Thai gold data from `price_cache` or live market baseline in < 100ms, and fix Admin 7-day chart distortion.
4. Comprehensive testing (`pytest tests/`) & Team Lead Zoro Thai supervisory sign-off report.

## Phase 0: Survey & Scope Exploration
- Dispatch 3 Explorers in parallel:
  - Explorer 1: R1 — 30d and 90d horizons, frontend dropdown, route validation, error bounds, evaluation payload.
  - Explorer 2: R2 — Self-healing fallback mechanism, root cause of "ข้อมูลจริงยังไม่พร้อม", DB row threshold bypass, bootstrap logic, safety bounds enforcement.
  - Explorer 3: R3 — `/api/historical`, elimination of `yfinance` network delay, local `price_cache` / live baseline fallback, Admin 7-day chart rendering and styling.
- Aggregate reports into updated `PROJECT.md` Feature Inventory and Milestone decomposition.

## Phase 1: Milestone 1 — Forecast Engine Restoration (R1 & R2)
- Assigned to Agent A (Forecasting & Statistics Engineer)
- Explorer -> Worker -> Reviewers (2) -> Challengers (2) -> Forensic Auditor -> Gate.

## Phase 2: Milestone 2 — Admin Chart Performance & Real Baseline Data (R3)
- Assigned to Agent B (Data Pipeline & API Performance Specialist)
- Explorer -> Worker -> Reviewers (2) -> Challengers (2) -> Forensic Auditor -> Gate.

## Phase 3: Milestone 3 — End-to-End Verification & Zoro Thai Sign-off
- Comprehensive test runner (`pytest tests/`).
- Team Lead Zoro comprehensive supervisory review and Thai milestone conclusion.
- Final victory notification to Sentinel.
