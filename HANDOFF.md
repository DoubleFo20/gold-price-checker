# Handoff Document — Gold Price Checker

**Date:** 2026-09-10  
**Reason:** Codex reaching usage limit — handoff to next agent  
**Branch:** main (origin/main up to date)  
**Last commit:** 97edcea — feat: add evidence-backed gold forecasting

---

## Current Task

**M4 Security and Infrastructure Hardening** — adding Flask-Limiter rate limiting,
DB connection pooling, email delivery logging, session revocation on password change,
REST-style URL aliases for all routes, and a morning price summary scheduler job.

---

## Completed Work (This Sprint)

1. **Flask-Limiter** (pi/utils/limiter.py [NEW]):
   - Global limiter: 200/day, 50/hour
   - Per-route limits on login, register, change-password: 5/min
   - OPTIONS requests exempt (CORS preflight)
   - 429 JSON error handler with Thai message in create_app.py

2. **DB Connection Pool** (pi/database/connection.py):
   - Added PooledDB (DBUtils) with optional import fallback
   - New functions: init_db_pool(), _get_connection_config()
   - Env vars: DB_POOL_MIN_CACHED, DB_POOL_MAX_CACHED, DB_POOL_MAX_CONNECTIONS

3. **Email Delivery Logging** (pi/services/email_service.py):
   - log_email_attempt() writes to email_logs table on every send/fail
   - _send_smtp() updated to accept user_id and call log_email_attempt
   - send_morning_price_summary_email_smtp() added

4. **Morning Price Summary Scheduler** (pi/services/scheduler.py):
   - job_morning_price_summary() — fetches live prices and dispatches to:
     email, LINE, web push, in-app notifications for opted-in users
   - NOTE: function is written but NOT yet registered with APScheduler

5. **Route URL Aliases** (auth_routes.py, user_routes.py, alerts.py):
   - All /api/api/* legacy routes now ALSO respond to:
     - /api/* (clean REST)
     - /api/*.php (PHP-compat without double prefix)
   - Affects: login, register, check-session, update-profile, change-password,
     update-push, generate-line-code, update-line, save-forecast,
     get-saved-forecasts, notifications/list, alerts/create|list|delete

6. **Session Revocation on Password Change** (auth_routes.py):
   - DELETE FROM sessions WHERE user_id after password update
   - Clears session cookie in HTTP response

7. **Service Worker** (sw.js):
   - Cache version bumped, offline fallback improved

8. **Frontend Config** (js/config.js):
   - API URL helpers updated to use new /api/* path structure

---

## Files Changed

| File | Status | Description |
|---|---|---|
| api/app/create_app.py | Modified | limiter.init_app(), 429 handler, jsonify import |
| api/database/connection.py | Modified | PooledDB pool, _get_connection_config, init_db_pool |
| api/routes/alerts.py | Modified | Added /api/alerts/* route aliases |
| api/routes/auth_routes.py | Modified | Rate limits, URL aliases, session revocation |
| api/routes/user_routes.py | Modified | URL aliases for profile/user endpoints |
| api/services/email_service.py | Modified | log_email_attempt, send_morning_price_summary_email_smtp |
| api/services/scheduler.py | Modified | job_morning_price_summary |
| js/config.js | Modified | API URL path updates |
| js/script.js | Modified | Minor config reference update |
| requirements.txt | Modified | Added flask-limiter, dbutils |
| sw.js | Modified | Cache version bump, offline fallback |
| api/utils/limiter.py | NEW (untracked) | Limiter singleton module |
| tests/e2e/ | NEW (untracked) | 190 E2E tests (4 tiers) |
| tests/test_m1_challenger_edge_cases.py | NEW (untracked) | Security edge case tests |
| tests/test_m1_security_db.py | NEW (untracked) | DB security tests |
| .agents/ | NEW (untracked) | Agent config folder |
| ORIGINAL_REQUEST.md | NEW (untracked) | Original project brief |
| TEST_INFRA.md | NEW (untracked) | E2E test architecture docs |
| TEST_READY.md | NEW (untracked) | E2E test results/validation |

---

## Test Results

| Suite | Count | Result | Command |
|---|---|---|---|
| E2E Tier 1-4 (with M4 changes) | 190 | PASSED (87.68s) | .venv\Scripts\python.exe -m pytest tests/e2e/ -q |

**Note:** Tests use in-memory DB mock; limiter.enabled is NOT set to False in conftest
(rate limiter bypassed via isolated sub-app instances in rate-limit tests).

---

## Remaining Work

1. **Register morning job with APScheduler** — wire job_morning_price_summary()
   into the scheduler start block (likely in create_app.py or a scheduler init module).
   Suggested cron: every day at 07:00 local time.

2. **Verify DB pool on Koyeb** — ensure DBUtils is importable in Koyeb environment;
   requirements.txt now includes dbutils>=1.3.

3. **Deploy and smoke test** — push to Koyeb, run health check endpoint,
   confirm /api/health returns 200 and /api/auth/login rate-limits after 5 attempts.

4. **Optional: Redis for limiter storage** — currently uses memory://, fine for single-instance.
   Set RATELIMIT_STORAGE_URI=redis://... for multi-process Gunicorn workers.

---

## Known Issues / Blockers

- **No blockers.** All 190 E2E tests pass with current code.
- The venv Python path is .venv\Scripts\python.exe (Python 3.11 inside venv,
  system Python is 3.12 without project deps).
- job_morning_price_summary() exists but is not scheduled — it is dead code until wired up.

---

## Recommended Next Step

`
1. git pull (confirm branch is main)
2. Register morning job in APScheduler (see api/services/scheduler.py bottom of file)
3. Run: .venv\Scripts\python.exe -m pytest tests/e2e/ -q  (should show 190 passed)
4. git push && deploy to Koyeb
5. Smoke test: curl https://<koyeb-url>/api/health
`

---

## Environment

- Python venv: .venv\Scripts\python.exe (Python 3.11)
- Database: Aiven MySQL with SSL (set DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_SSL_CA in .env)
- Run API: cd api && gunicorn app.wsgi:app -w 2 -b 0.0.0.0:5000 (see Procfile)
