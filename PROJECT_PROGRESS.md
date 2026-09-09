# Gold Price Checker — Project Progress

_Last updated: 2026-09-10 (Codex handoff)_

---

## Overall Status: **In Progress — Handoff Ready**

---

## Completed Milestones

### ✅ M0 — Project Foundation
- XAMPP/PHP + Flask hybrid backend scaffolded
- MySQL schema designed (17 tables)
- Static frontend (index.html, style.css) built

### ✅ M1 — Core Backend (Flask API)
- App factory pattern (create_app.py)
- Service layer: auth, gold_price, forecast, notification, line, email
- Routes: auth, alerts, user, price, admin, forecast, export, health
- get_db_connection() with SSL/TLS (Aiven-managed MySQL)
- Deployment configs: Render, Koyeb + Aiven

### ✅ M2 — AI Forecasting Engine
- Multi-model support: ensemble, linear_regression, arima, lstm
- Forecast horizons: 7, 14, 30 days with confidence intervals
- Model evaluation metrics: MAE, RMSE, MAPE, Directional Accuracy
- Markdown quality-gate report generation
- Evidence-backed forecast rationale (commit 97edcea)

### ✅ M3 — E2E Test Suite (190 tests)
- 4-Tier test architecture: Feature Coverage, Boundaries, Pairwise, Real-World Scenarios
- 100% pass rate on 190 tests (no external dependencies — in-memory DB mock)
- Test infra documented: TEST_INFRA.md, TEST_READY.md

### ✅ M4 — Security and Route Hardening (current sprint — unstaged)
- Flask-Limiter integration: api/utils/limiter.py + create_app.py wired
  - Login: 5 req/min; Register: 5 req/min; Change Password: 5 req/min
  - Global defaults: 200/day, 50/hour
  - 429 JSON error handler with Thai language message
- Session revocation on password change: all sessions deleted after password update
- DB Connection Pooling (DBUtils.PooledDB): thread-safe pool with configurable min/max cached
- Email Delivery Logging: log_email_attempt() writes to email_logs table
- Morning Price Summary Job: job_morning_price_summary() in scheduler
- REST-style URL aliases: all /api/api/* routes also respond on /api/* and /api/*/*.php
- Frontend Service Worker enhanced: cache versioning + offline fallback improved
- Security fix (change-password): session cookie cleared in response

---

## Feature Completion

| Feature | Status |
|---|---|
| F1 — Registration | Complete |
| F2 — Email Verification | Complete |
| F3 — Login and Sessions | Complete |
| F4 — Password Reset | Complete |
| F5 — Live Gold Price Scraping | Complete |
| F6 — Historical Price Analysis | Complete |
| F7 — Price Discrepancy Detection | Complete |
| F8 — CSV/JSON Export | Complete |
| F9 — Alert Creation and Rules | Complete |
| F10 — Email Notifications | Complete (+ delivery logging) |
| F11 — LINE Notify Webhook | Complete |
| F12 — In-App and Push Notifications | Complete |
| F13 — AI Price Forecasting Models | Complete |
| F14 — Forecast Evaluation Metrics | Complete |
| F15 — Admin User Management | Complete |
| F16 — Rate Limiting and Security Gates | Complete (Flask-Limiter wired) |
| F17 — Quality Validation and Markdown Report | Complete |

---

## Pending / Remaining

| Item | Priority | Notes |
|---|---|---|
| Run full E2E suite post-M4 | High | Verify limiter.enabled=False in conftest still holds |
| Morning summary job APScheduler wire-up | Medium | job_morning_price_summary() written, not yet registered |
| DB pool Aiven integration test | Medium | DBUtils optional dep added to requirements.txt |
| Deploy and smoke test on Koyeb | Low | After test confirmation |

---

## Test Results (last known good)

- 190 E2E tests — 100% pass (pre-M4 hardening, commit 97edcea)
- M4 changes are being committed; re-run suite after commit

## Deployment Info
- Backend: Koyeb (Procfile + render.yaml)
- Database: Aiven managed MySQL (SSL/TLS enforced)
- Frontend: served from XAMPP htdocs or Koyeb static
