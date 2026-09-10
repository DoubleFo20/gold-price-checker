# Original User Request

## 2026-09-09T15:35:56Z

Complete the full-stack Gold Price Checker system (gold-price-checker) to 100% production readiness. The system features an advanced dual-agent adversarial gold price forecasting engine with strict min-max bounds, a high-reliability notification engine (LINE, Email, Web Push), complete backend hardening, automated GitHub synchronization, and end-to-end supervision and Thai reporting by Team Lead Zoro.

Working directory: d:\xampp\htdocs\gold-price-checker
Integrity mode: development

## Team Structure & Responsibilities

- **Team Lead Zoro**: Oversees the entire lifecycle, assigns work packages, reviews code quality and test results, ensures models do not drift, and writes detailed milestone reports and final conclusions in Thai.
- **Agent A (Forecasting Lead)**: Builds and tunes core technical and statistical models for 7-day and 30-day gold price projections.
- **Agent B (Adversarial & Consensus Specialist)**: Challenges Agent A's projections using macroeconomic variables (USD/THB exchange rates, global spot momentum, market volatility). If predictions differ by > 3%, engages in algorithmic debate to reach a robust consensus forecast with strict min-max safety boundaries.
- **Agent C (Backend Security & Database Architecture)**: Implements rate limiting on authentication routes, enforces immediate session invalidation on password change, implements database connection pooling, and deprecates remaining legacy PHP scripts.
- **Agent D (Notifications & Auth Flow Champion)**: Upgrades and hardens the real-time alert engine (LINE Messaging API webhook, SMTP email delivery, Web Push Service Worker), and implements full email verification and password reset flows.
- **Agent E (QA Test & GitHub Pusher)**: Develops automated test suites (pytest), validates backtesting accuracy (MAPE < 5%), and pushes all verified commits to GitHub (DoubleFo20/gold-price-checker on branch main).

## Requirements

### R1. High-Precision Gold Forecasting Engine with Dual-Agent Debate
- Generate reliable 7-day and 30-day forward gold price forecasts (Thai Baht gold bar and World Spot gold).
- Integrate a dual-agent consensus mechanism:
  - Agent A generates technical trend projection.
  - Agent B generates macro/FX-adjusted projection.
  - If discrepancy exceeds 3%, reconcile via weighted consensus.
  - Apply strict Min-Max safety boundaries to prevent hallucinated or extreme outlier predictions.
- Validate predictions through automated backtesting against historical price movements.

### R2. Mission-Critical Notification & Alert System
- Harden real-time price trigger checks against live prices (above/below targets).
- Ensure multi-channel dispatch reliability:
  - LINE Notify / LINE Messaging API push.
  - HTML SMTP Email alerts with verification and delivery tracking.
  - Browser Web Push Notifications via Service Worker (sw.js).
- Add scheduled notifications for daily morning price summaries and verified forecast results.

### R3. Backend Security & Connection Pooling
- Implement rate limiting (e.g., Flask-Limiter) on /login, /register, and sensitive endpoints.
- Ensure changing passwords immediately revokes all existing active session tokens in the database.
- Transition DB access from single connections to a persistent Connection Pool.
- Standardize all frontend API calls through the unified Flask backend.

### R4. Automated Testing & Continuous GitHub Synchronization
- Execute comprehensive test suites (pytest) verifying auth, alerts, forecasting, and API health.
- After each verified milestone, commit clean git commits and push directly to GitHub (origin/main).

### R5. Team Lead Zoro Supervisory Evaluation & Thai Reporting
- Team Lead Zoro reviews every component before sign-off, confirms accuracy metrics, and provides an executive summary in Thai detailing completed tasks, forecast validation, and operational instructions.

## Acceptance Criteria

### Forecasting Performance
- [ ] 7-day and 30-day forecast endpoints return structured predictions with min_price, max_price, consensus_price, and confidence rating.
- [ ] Forecast outputs strictly adhere to calculated Min-Max safety bounds without price drift.
- [ ] Dual-agent debate mechanism resolves any discrepancy > 3% smoothly with documented consensus weights.
- [ ] Historical backtest passes with Mean Absolute Percentage Error (MAPE) < 5%.

### Alert & Notification Reliability
- [ ] Triggered price alerts successfully queue and dispatch across configured channels (LINE, Email, Web Push).
- [ ] Service Worker push event listener handles background push payloads properly.
- [ ] Email verification and password reset token workflows function end-to-end.

### Security & Architecture
- [ ] Brute-force attacks are throttled by rate limiting on auth endpoints.
- [ ] Password updates immediately invalidate all prior active session tokens for that user.
- [ ] Database connection pool maintains connections efficiently under load.

### Delivery & Synchronization
- [ ] All test suites pass 100% without failures.
- [ ] All commits are pushed to remote GitHub repository DoubleFo20/gold-price-checker on main.
- [ ] Final evaluation and milestone walkthrough is provided in Thai by Team Lead Zoro.

## 2026-09-09T21:50:57Z

# Teamwork Project Prompt — Forecast Engine Restoration & Admin Chart Optimization

> Status: Launched — Executing via Teamwork Multi-Agent System
> Goal: Fix forecasting failure, restore 1, 7, 30, 90-day horizons, resolve "ข้อมูลจริงยังไม่พร้อม" error with reliable auto-fallback, and eliminate distorted/slow Yahoo Finance dependency from Admin chart.
> Requested team: Team Lead Zoro, Agent A (Forecasting & Statistics Engineer), Agent B (Data Pipeline & API Performance Specialist)

Fix the production forecasting failure ("ข้อมูลจริงยังไม่พร้อมสำหรับการพยากรณ์"), restore the missing 30-day and 90-day forecast horizons across UI and backend, and eliminate the slow, distorted Yahoo Finance data fetch from the Admin dashboard chart by switching to fast local DB and clean real-price baseline data.

Working directory: `d:\xampp\htdocs\gold-price-checker`
Integrity mode: development

## Requirements

### R1. Restore 30-Day and 90-Day Forecast Horizons
- In `components/6-forecast.html`, add `<option value="30">30 วัน (1 เดือน)</option>` and `<option value="90">90 วัน (3 เดือน)</option>` to the `#forecast-period` dropdown alongside 1 and 7 days.
- In `api/routes/forecast_routes.py` and `api/services/forecast_service.py`, expand `SUPPORTED_PERIODS` from `(1, 7, 30)` to `(1, 7, 30, 90)`.
- Configure error bounds (`_interval_errors`) and evaluation payload (`_evaluation_payload`) to handle 90-day projection intervals smoothly.

### R2. Resolve "ข้อมูลจริงยังไม่พร้อมสำหรับการพยากรณ์" (Self-Healing Production Fallback)
- Root cause: On production/Render, if `price_cache` has fewer than 500 verified rows or `forecast_model_metrics` lacks a selected champion, `ForecastUnavailableError` is raised, throwing HTTP 503 and blocking users.
- Add an autonomous fallback/bootstrap mechanism:
  - If official verified champion data is ready in DB, use it.
  - If official champion or 500 rows are not ready in DB, automatically bootstrap forecasting using all available historical price points or the current live market price with Holt ETS / ARIMA / Momentum drift models.
  - Ensure `/api/forecast` **always returns 200 OK** with realistic, bounded price forecasts (max 2.5% for 1d, 7% for 7d, 12% for 30d, 18% for 90d) and evaluation metadata, never crashing or displaying the "ข้อมูลจริงยังไม่พร้อม" alert.

### R3. Remove / Fix Distorted Yahoo Finance Fetch in Admin Chart
- Cut out synchronous external Yahoo Finance (`yfinance`) calls from `/api/historical` for the Admin chart to avoid 12-second latency and distorted data.
- Ensure `/api/historical` immediately serves real Thai gold data from `price_cache` or a clean daily baseline anchored on the live market price (`bar_sell`), responding in < 100ms.
- Ensure the Admin 7-day chart renders crisp, realistic gold prices with proper labels (no dense empty grid lines).

## Acceptance Criteria

### Forecasting Reliability & Options
- [ ] `#forecast-period` dropdown contains 1 day, 7 days, 30 days (1 month), and 90 days (3 months).
- [ ] `/api/forecast?period=30` and `/api/forecast?period=90` return valid JSON with `forecast`, `upper_bound`, `lower_bound`, and `evaluation` data.
- [ ] When testing without 500 verified DB rows, the forecast endpoint still returns 200 OK with valid predictions instead of HTTP 503 error.
- [ ] Clicking "สร้างการพยากรณ์" on the frontend displays results, chart, and metrics for all 4 periods without popup errors.

### Admin Chart & Performance
- [ ] `/api/historical?days=7` responds in under 200ms without depending on blocking Yahoo Finance network calls.
- [ ] Admin dashboard chart renders clean 7-day price trends without distorted grids or missing lines.
- [ ] All automated tests pass (`pytest tests/`).

---
*Next: when approved → delegate via invoke_subagent (see Delegation Protocol)*

