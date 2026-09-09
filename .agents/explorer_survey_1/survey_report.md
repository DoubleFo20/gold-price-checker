# Codebase Survey & Architecture Report: Gold Price Checker

**Agent**: `explorer_survey_1`  
**Timestamp**: 2026-09-09T15:45:00Z  
**Target Repository**: `DoubleFo20/gold-price-checker` (`d:\xampp\htdocs\gold-price-checker`)  
**Mission**: Map project layout, server frameworks, database setup, legacy PHP scripts, frontend integrations, environment dependencies, and test suite.

---

## 1. Project Directory Structure & Architecture

### 1.1 Directory Layout Overview

```
gold-price-checker/
├── .agents/                      # Multi-agent coordination metadata
├── .venv/                        # Python 3.11.9 Virtual Environment
├── .python-version               # Specifies 3.11.9
├── Procfile                      # Koyeb/Heroku Procfile (gunicorn --chdir api server:app)
├── render.yaml                   # Render deployment configuration
├── DEPLOY_KOYEB_AIVEN.md         # Architecture & production deployment runbook
├── requirements.txt              # Python pip dependencies
├── style.css                     # Primary stylesheet (~78KB)
├── sw.js                         # Service worker for Web Push notifications
├── index.html                    # Single Page Application (SPA) entrypoint
├── local-legacy.html             # Legacy local mode redirector (?legacy_local=1)
├── profile_system.html           # Standalone profile modal markup
├── profile_test.html             # Standalone profile test page
├── clear_login.html / logout.html# Utility session clearing pages
│
├── admin/                        # Modern Admin Dashboard (Static Single Page App)
│   ├── index.html                # Admin dashboard HTML
│   ├── css/admin.css             # Admin styling
│   └── js/admin.js               # Admin frontend controller (calls Flask /api/admin/*)
│
├── components/                   # Modular HTML partials loaded via fetch()
│   ├── 0-hero-section.html
│   ├── 1-price-today.html        # Live Thai bar/ornament and World spot cards
│   ├── 2-live-chart.html         # TradingView / Canvas live price chart
│   ├── 3-historical-chart.html   # Historical gold price chart
│   ├── 4-news.html               # Newsfeed section
│   ├── 5-calculator.html         # Gold weight & value calculator
│   ├── 6-forecast.html           # Gold price forecasting panel (AI / statistical)
│   ├── 7-alerts.html             # Price alert configuration panel
│   ├── 8-economic-calendar.html  # Economic events widget
│   └── profile.html              # User profile panel partial
│
├── js/                           # Frontend JavaScript
│   ├── config.js                 # API base URL configuration & runtime mode flags
│   ├── script.js                 # Main SPA application logic (~97KB, 2,233 lines)
│   ├── profile_fix.js            # Profile modal enhancement utility
│   └── patch.py                  # Utility patch script
│
├── sql/                          # Root SQL dumps
│   └── goldapidb.sql             # Legacy phpMyAdmin dump with sample dev rows
│
├── tests/                        # Automated test suite
│   ├── __init__.py
│   ├── test_deployment.py        # 12 deployment, health, auth error & notification tests
│   └── test_forecasting.py       # 15 data-quality, walk-forward backtest & model tests
│
└── api/                          # Unified Backend Service (Flask + Legacy PHP)
    ├── server.py                 # Flask entrypoint for development & Gunicorn module alias
    ├── .env / .env.example       # Environment configuration files
    ├── .aiven-ca.pem             # Aiven MySQL SSL CA Certificate
    ├── app/
    │   └── create_app.py         # Flask Application Factory pattern
    ├── routes/                   # Flask Blueprints
    │   ├── main.py               # Health checks (/health, /health/db), static file serving
    │   ├── prices.py             # Gold prices (/api/thai-gold-price, /api/world-gold-price, /api/intraday, /api/historical, /api/news)
    │   ├── auth_routes.py        # Authentication & legacy PHP shim routes
    │   ├── alerts.py             # Price alerts CRUD & PHP compat routes
    │   ├── forecast_routes.py    # Forecasting API (/api/forecast, /api/forecast/send-email)
    │   ├── user_routes.py        # Profile, LINE linking, Web Push, Notifications
    │   ├── jobs.py               # Cron job trigger (/api/jobs/run) & VAPID public key
    │   ├── webhook.py            # LINE Messaging API Webhook (/webhook)
    │   └── admin.py              # Admin REST endpoints (/api/admin/*)
    ├── services/                 # Backend business logic
    │   ├── auth.py               # User session resolution & authentication guards
    │   ├── gold_price.py         # Scraping Thai Gold Traders Assoc & Yahoo Finance
    │   ├── historical.py         # Historical price caching and retrieval
    │   ├── forecast_models.py    # ARIMA, Holt ETS, Drift, Naive walk-forward backtesters
    │   ├── forecast_service.py   # Forecast data orchestration and evaluation
    │   ├── forecast_data.py      # Price series continuity & quality validation (500 days)
    │   ├── line_service.py       # LINE push, reply, profile fetching
    │   ├── notification.py       # Multi-channel alert dispatch (In-app, LINE, Web Push, Email)
    │   ├── email_service.py      # SMTP HTML email sender
    │   ├── scheduler.py          # Unified scheduled jobs runner (runs once per job trigger)
    │   └── bot_exchange.py       # Bank of Thailand USD/THB reference rate client
    ├── database/
    │   └── connection.py         # PyMySQL DB connector & auto-column migration helper
    ├── config/                   # Configuration files (Python & PHP)
    │   ├── base.py / development.py / production.py # Flask config objects
    │   └── app.php / config.php / database.php / line_helper.php # Legacy PHP config
    ├── scheduler/
    │   └── jobs.py               # Development-mode background worker thread wrapper
    ├── sql/                      # Clean production DB migrations
    │   ├── goldapidb.sql         # Clean provider-neutral schema (17 tables, no seeded data)
    │   ├── forecast_model_upgrade.sql
    │   ├── alter_saved_forecasts_add_actual.sql
    │   ├── create_alerts_table.sql
    │   ├── create_saved_forecasts.sql
    │   └── run_alter_forecasts.php
    ├── tools/                    # Operational scripts (Python & PHP)
    │   ├── evaluate_forecast_models.py
    │   ├── import_gold_history.py
    │   ├── import_bot_exchange.py
    │   ├── apply_forecast_upgrade.py
    │   ├── backup_database.py
    │   ├── verify_forecast_release.py
    │   ├── test_email.php / verify_env.php / view_logs.php
    │   └── ngrok.exe             # Tunneling tool binary
    ├── cron/                     # Legacy PHP cron scripts
    │   ├── check_alerts.php
    │   └── verify_forecasts.php
    ├── admin/                    # Legacy PHP Admin Panel (SB Admin 2)
    └── api/                      # Legacy PHP API endpoints (`api/api/*`)
```

---

## 2. Database Setup & Connection Handling

### 2.1 Database Tables Catalog

The canonical database schema is defined in `api/sql/goldapidb.sql` (and documented in `DEPLOY_KOYEB_AIVEN.md`). It contains **17 tables**:

| # | Table Name | Purpose / Responsibility | Foreign Keys / Key Indexes |
|---|------------|--------------------------|----------------------------|
| 1 | `users` | User accounts, credentials (bcrypt), role (`user`/`admin`), verification, LINE user ID, push subscription JSON | `uq_users_email` (UNIQUE), `idx_users_email`, `idx_users_last_login` |
| 2 | `sessions` | Active login session tokens (64-char hex), expiry, IP, user-agent | FK `users(id)` ON DELETE CASCADE, `uq_sessions_token`, `idx_sessions_user_expires` |
| 3 | `price_alerts` | User-defined price thresholds, gold type (`bar`/`ornament`/`world`), direction (`above`/`below`), trigger status | FK `users(id)` ON DELETE CASCADE, `uq_alert_active` |
| 4 | `calculation_history` | Historical logs of user calculations on gold weight/value | FK `users(id)` ON DELETE CASCADE, `idx_calc_user_date` |
| 5 | `saved_forecasts` | User-bookmarked forecast projections, predicted vs actual prices, evaluation error | FK `users(id)` ON DELETE CASCADE, `idx_forecasts_due` |
| 6 | `rate_limits` | Rolling window rate limiting log (identifier, action, timestamp epoch) | `idx_rate_lookup (identifier, action, ts_unix)` |
| 7 | `email_logs` | Audit trail of dispatched SMTP emails, recipients, subjects, status, error messages | FK `users(id)` ON DELETE SET NULL, `idx_email_status_date` |
| 8 | `price_cache` | Daily official gold prices (bar, ornament, spot USD/THB, BOT USD/THB, quality status) | `uq_pricecache_date` (UNIQUE) |
| 9 | `forecast_model_metrics` | Walk-forward backtest evaluation metrics JSON for candidate models | `uq_forecast_model_run (model_name, model_version, trained_through)` |
| 10 | `forecast_predictions` | Canonical daily forecast projections (1-day, 7-day) with upper/lower bounds | `uq_forecast_prediction (model_version, trained_through, horizon_step)` |
| 11 | `api_request_logs` | HTTP request telemetry, latency ms, status code, route | FK `users(id)` ON DELETE SET NULL |
| 12 | `auth_logs` | Audit log for auth events (`login_success`, `login_failed`, `logout`) | FK `users(id)` ON DELETE SET NULL |
| 13 | `cron_job_runs` | Execution log for background scheduled jobs | `idx_cron_name_time` |
| 14 | `activity_logs` | General administrative and user activity logging | FK `users(id)` ON DELETE SET NULL |
| 15 | `notifications` | In-app user notifications (type: `price_alert`, `forecast_result`, `system`) | FK `users(id)` ON DELETE CASCADE, `idx_notif_user_unread` |
| 16 | `email_verifications` | Email verification tokens with expiration timestamps | FK `users(id)` ON DELETE CASCADE, `token` (UNIQUE) |
| 17 | `password_resets` | Password reset tokens with 30-minute expiration timestamps | FK `users(id)` ON DELETE CASCADE, `token` (UNIQUE) |

### 2.2 Connection Handling Analysis

#### Python / Flask Backend (`api/database/connection.py`)
- **Current Implementation**:
  ```python
  def get_db_connection():
      ...
      return pymysql.connect(
          host=host, user=user, password=password, database=database,
          port=port, cursorclass=pymysql.cursors.DictCursor, **connect_options
      )
  ```
- **Deficiencies Identified**:
  1. **No Connection Pooling**: Every single route and query opens an individual TCP connection to MySQL and closes it manually in a `finally` block. Under concurrent load (or Koyeb/Aiven latency), this introduces latency spikes and risks exhausting database connections.
  2. **Auto-column Alteration Side-Effects**: `_ensure_users_columns` runs DDL `ALTER TABLE` dynamically on missing column errors. While forgiving during development, dynamic DDL during user requests in production causes table metadata locks.
  3. **Requirement R3 Violation**: Requirement R3 explicitly mandates: *"Transition DB access from single connections to a persistent Connection Pool."* (e.g., using `DBUtils.pooled_db.PooledDB`).

#### Legacy PHP Backend (`api/config/database.php`)
- Uses PHP PDO (`new PDO("mysql:host=...;dbname=...", ...)`) with no pooling.

---

## 3. Legacy PHP Scripts Inventory & Migration Analysis

There are **48 PHP files** across the workspace. Below is the complete catalog grouped by category with their status and migration roadmap:

### 3.1 Authentication Subsystem (`api/api/auth/`) — 11 files

| PHP File Path | Purpose | Current Flask Equivalent | Migration / Hardening Action Needed |
|---------------|---------|--------------------------|-------------------------------------|
| `api/api/auth/login.php` | User login, session creation | `@auth_bp.route("/api/api/auth/login.php")` | Expose clean `POST /api/auth/login`, apply rate limiting (R3), keep compat alias. |
| `api/api/auth/register.php` | User registration | `@auth_bp.route("/api/api/auth/register.php")` | Expose clean `POST /api/auth/register`, apply rate limiting (R3), trigger verification email. |
| `api/api/auth/check_session.php` | Verify session cookie | `@auth_bp.route("/api/api/auth/check_session.php")` | Expose clean `GET /api/auth/me` and `GET /api/auth/check-session`. |
| `api/api/auth/logout.php` | Delete session from DB & clear cookie | `@auth_bp.route("/api/api/auth/logout.php")` | Expose clean `POST /api/auth/logout`. |
| `api/api/auth/change_password.php` | Change user password | `@auth_bp.route("/api/api/auth/change_password.php")` | **CRITICAL FIX**: Current Flask code updates hash but does NOT invalidate active sessions! Must add `DELETE FROM sessions WHERE user_id = %s` (R3 requirement). Expose clean `POST /api/auth/change-password`. |
| `api/api/auth/update_profile.php` | Update user name | `@auth_bp.route("/api/api/auth/update_profile.php")` | Expose clean `PUT /api/auth/profile`. |
| `api/api/auth/forgot.php` | Generate reset token, send email | **MISSING IN FLASK**. Broken in PHP (requires non-existent `includes/email.php`). | Implement in Flask: `POST /api/auth/forgot-password` with HTML SMTP email dispatch (R2). |
| `api/api/auth/reset.php` | Reset password using token | **MISSING IN FLASK**. | Implement in Flask: `POST /api/auth/reset-password` (validates `password_resets` table, resets hash, purges all user sessions). |
| `api/api/auth/verify.php` | Confirm email verification token | **MISSING IN FLASK**. | Implement in Flask: `GET /api/auth/verify-email?token=...`. |
| `api/api/auth/resend_verify.php` | Resend verification email | **MISSING IN FLASK**. Broken in PHP (missing `includes/email.php`). | Implement in Flask: `POST /api/auth/resend-verification`. |
| `api/api/auth/me.php` | Return current user info | **MISSING IN FLASK**. | Integrate into `GET /api/auth/me`. |

### 3.2 Price Alerts Subsystem (`api/api/alerts/`) — 3 files

| PHP File Path | Purpose | Current Flask Equivalent | Migration Action |
|---------------|---------|--------------------------|------------------|
| `api/api/alerts/create.php` | Create price alert | Clean: `POST /api/alerts/create`, Compat: `POST /api/api/alerts/create.php` | Deprecate PHP file. Clean endpoint already exists. |
| `api/api/alerts/list.php` | List active alerts for user | Clean: `GET /api/alerts`, Compat: `GET /api/api/alerts/list.php` | Deprecate PHP file. |
| `api/api/alerts/delete.php` | Delete price alert | Clean: `DELETE /api/alerts/<id>`, Compat: `POST /api/api/alerts/delete.php` | Deprecate PHP file. |

### 3.3 User Profile, LINE & Web Push (`api/api/profile/`, `api/api/user/`, `api/api/notifications/`) — 7 files

| PHP File Path | Purpose | Current Flask Equivalent | Migration Action |
|---------------|---------|--------------------------|------------------|
| `api/api/profile/generate_line_code.php` | Generate 6-digit LINE linking code | Registered only as `/api/api/profile/generate_line_code.php` | Add clean route: `POST /api/profile/line-code`. |
| `api/api/profile/update_line.php` | Link LINE user ID to account | Registered only as `/api/api/profile/update_line.php` | Add clean route: `POST /api/profile/line`. |
| `api/api/profile/update_push.php` | Save Web Push subscription | Registered only as `/api/api/profile/update_push.php` | Add clean route: `POST /api/profile/push-subscription`. |
| `api/api/user/save_forecast.php` | Save user forecast bookmark | Registered only as `/api/api/user/save_forecast.php` | Add clean route: `POST /api/forecasts/save`. |
| `api/api/user/get_saved_forecasts.php` | Retrieve saved forecasts | Registered only as `/api/api/user/get_saved_forecasts.php` | Add clean route: `GET /api/forecasts/saved`. |
| `api/api/notifications/list.php` | List user in-app notifications | Registered only as `/api/api/notifications/list.php` | Add clean route: `GET /api/notifications`. |
| `api/api/notifications/mark_read.php` | Mark notification as read | Registered only as `/api/api/notifications/mark_read.php` | Add clean route: `POST /api/notifications/mark-read`. |

### 3.4 Proxies, Webhooks & Health (`api/api/proxy/`, `api/api/line/`, `api/api/health.php`) — 4 files

| PHP File Path | Purpose | Status in Flask |
|---------------|---------|-----------------|
| `api/api/proxy/historical.php` | Alpha Vantage gold proxy | Replaced by `api/routes/prices.py: /api/historical`. PHP script is broken (requires non-existent `includes/rate_limit.php`). Safe to delete/deprecate. |
| `api/api/proxy/news.php` | NewsAPI gold news proxy | Replaced by `api/routes/prices.py: /api/news`. Safe to delete/deprecate. |
| `api/api/line/webhook.php` | LINE Messaging Webhook | Replaced by `api/routes/webhook.py: /webhook` with HMAC-SHA256 signature verification. Safe to deprecate. |
| `api/api/health.php` | PHP Healthcheck | Replaced by `api/routes/main.py: /health` and `/health/db`. Safe to deprecate. |

### 3.5 Cron Scripts (`api/cron/`) — 2 files

| PHP File Path | Purpose | Python Replacement |
|---------------|---------|--------------------|
| `api/cron/check_alerts.php` | Periodic alert checker | Replaced by `services/scheduler.py:run_scheduled_jobs_once()` triggered via `POST /api/jobs/run`. |
| `api/cron/verify_forecasts.php` | Forecast backtesting verification | Replaced by `services/forecast_service.py:verify_canonical_predictions()`. |

### 3.6 Legacy Admin Subsystem (`api/admin/`) — 9 files

- Files: `api/admin/index.php`, `api/admin/template.php`, `api/admin/pages/activity_logs.php`, `api/admin/pages/dashboard.php`, `api/admin/pages/delete_user.php`, `api/admin/pages/edit_user.php`, `api/admin/pages/price_alerts.php`, `api/admin/pages/update_user.php`, `api/admin/pages/users.php`.
- **Status**: Completely superseded by `admin/index.html` + `admin/js/admin.js` communicating with Flask blueprint `api/routes/admin.py`. Flask already redirects `/api/admin` requests to `/admin/` in `routes/main.py`. These PHP files are obsolete.

### 3.7 PHP Configurations & Utilities (`api/config/`, `api/tools/`, `api/sql/`, etc.) — 12 files

- `api/config/app.php`, `api/config/config.php`, `api/config/database.php`, `api/config/line_helper.php`
- `api/setup_forecast2.php`, `api/setup_forecast_table.php`
- `api/sql/run_alter_forecasts.php`
- `api/tools/test_email.php` (broken, requires missing `includes/email.php`)
- `api/tools/verify_env.php`, `api/tools/view_logs.php`
- `mock_system/api/mock_alert.php` (empty file)
- `test_api.php` (root dummy file)

---

## 4. Frontend Integration Analysis & Standardization Strategy

### 4.1 Frontend API Call Mechanisms

Frontend JavaScript currently uses an inconsistent dual-base scheme configured in `js/config.js`:
- `PYTHON_API_URL`: Points to Python server (e.g., `http://127.0.0.1:5000` or origin).
- `PHP_API_BASE`:
  - When on localhost and `_forceLocalApi` is false: evaluates to `"api/api"`, causing requests to bypass Flask and hit Apache/PHP directly.
  - When deployed on Render or with `_forceLocalApi=true`: evaluates to `${_pythonApiUrl}/api/api`, sending requests to Flask's `.php` compatibility endpoints.

### 4.2 Endpoint Inventory across Frontend Code

| Caller | Current URL Requested | Standard Target Endpoint |
|--------|----------------------|--------------------------|
| `js/script.js:131` | `${PHP_API_BASE}/auth/login.php` | `/api/auth/login` |
| `js/script.js:169` | `${PHP_API_BASE}/auth/register.php` | `/api/auth/register` |
| `js/script.js:219` | `${PHP_API_BASE}/auth/forgot.php` | `/api/auth/forgot-password` |
| `js/script.js:237` | `${PHP_API_BASE}/auth/check_session.php` | `/api/auth/me` |
| `js/script.js:281` | `${PHP_API_BASE}/auth/logout.php` | `/api/auth/logout` |
| `js/script.js:646` | `buildPhpApiUrl('auth/update_profile.php')` | `/api/auth/profile` |
| `js/script.js:699` | `buildPhpApiUrl('auth/change_password.php')` | `/api/auth/change-password` |
| `js/script.js:429` | `${PHP_API_BASE}/user/save_forecast.php` | `/api/forecasts/save` |
| `js/script.js:464` | `${PHP_API_BASE}/user/get_saved_forecasts.php` | `/api/forecasts/saved` |
| `js/script.js:570, 863` | `${PHP_API_BASE}/alerts/list.php` | `/api/alerts` |
| `js/script.js:614` | `${PHP_API_BASE}/alerts/delete.php` | `/api/alerts/<id>` |
| `js/script.js:780` | `${PHP_API_BASE}/alerts/create.php` | `/api/alerts/create` |
| `js/script.js:1680` | `buildPhpApiUrl('notifications/list.php')` | `/api/notifications` |
| `js/script.js:1760` | `buildPhpApiUrl('notifications/mark_read.php')` | `/api/notifications/mark-read` |
| `js/script.js:1796` | `buildPhpApiUrl('profile/generate_line_code.php')` | `/api/profile/line-code` |
| `js/script.js:1834` | `buildPhpApiUrl('profile/update_line.php')` | `/api/profile/line` |
| `js/script.js:1965` | `buildPhpApiUrl('profile/update_push.php')` | `/api/profile/push-subscription` |
| `js/script.js:926` | `/api/thai-gold-price` | `/api/thai-gold-price` (Already Flask) |
| `js/script.js:986` | `/api/world-gold-price` | `/api/world-gold-price` (Already Flask) |
| `js/script.js:1183` | `/api/intraday` | `/api/intraday` (Already Flask) |
| `js/script.js:1295` | `/api/historical` | `/api/historical` (Already Flask) |
| `js/script.js:1615` | `/api/forecast?period=...` | `/api/forecast` (Already Flask) |
| `admin/js/admin.js:4` | `/api/api/auth/check_session.php` | `/api/auth/me` |
| `admin/js/admin.js:94` | `/api/api/auth/logout.php` | `/api/auth/logout` |
| `admin/js/admin.js:161`| `/api/admin/stats` | `/api/admin/stats` (Already Flask) |
| `admin/js/admin.js:237`| `/api/admin/price-history` | `/api/admin/price-history` (Already Flask) |
| `admin/js/admin.js:300`| `/api/admin/alerts` | `/api/admin/alerts` (Already Flask) |
| `admin/js/admin.js:334`| `/api/admin/users` | `/api/admin/users` (Already Flask) |
| `admin/js/admin.js:466`| `/api/admin/forecasts` | `/api/admin/forecasts` (Already Flask) |
| `admin/js/admin.js:493`| `/api/admin/logs` | `/api/admin/logs` (Already Flask) |
| `admin/js/admin.js:522`| `/api/jobs/run` | `/api/jobs/run` (Already Flask) |

### 4.3 Standardization Architecture Recommendation

1. **Unify `js/config.js`**:
   Remove the split between `PYTHON_API_URL` and `PHP_API_BASE`. Direct 100% of traffic to relative `/api/*` routes hosted on the Flask application.
2. **Dual-Route Support in Flask**:
   Keep the legacy `/api/api/*.php` paths as thin compatibility wrappers in Flask while declaring canonical clean REST routes (`/api/auth/*`, `/api/alerts/*`, `/api/profile/*`).
3. **No Apache/PHP Dependency**:
   The entire system can run fully independently with `python api/server.py` or `gunicorn`, fulfilling 100% cloud portability (Koyeb, Render, Railway, Docker).

---

## 5. Environment & Dependencies

### 5.1 Runtimes & Environments

- **Python Version**:
  - Specified in `.python-version`: `3.11.9`
  - Specified in `render.yaml`: `3.10.0`
  - Active virtual environment (`.venv`): `Python 3.11.9` (Path: `d:\xampp\htdocs\gold-price-checker\.venv\Scripts\python.exe`)
  - System Python: `Python 3.12` (`C:\Users\u937\AppData\Local\Programs\Python\Python312\python.exe`)
- **Node.js / Frontend Packages**:
  - No root `package.json`. Frontend requires no build step (Vanilla HTML/CSS/JS with CDN assets).

### 5.2 Dependencies & Gap Analysis (`requirements.txt`)

Current `requirements.txt` content:
```text
flask
flask-cors
requests
beautifulsoup4
yfinance
scikit-learn
numpy
lxml
statsmodels
python-dotenv
pymysql>=1.1.0
cryptography>=41.0.0
bcrypt>=4.1.2
pywebpush>=2.0.3
gunicorn
waitress
```

**Missing Production Requirements**:
1. `Flask-Limiter` — Needed for Requirement R3 (throttling brute-force attacks on auth endpoints).
2. `DBUtils` — Needed for Requirement R3 (persistent MySQL Connection Pooling: `PooledDB`).
3. `pytest` & `pytest-cov` — Mandated by Requirement R4 and Acceptance Criteria ("automated test suites (pytest)"). Currently only `unittest` is executable.

---

## 6. Existing Tests & Verification Suite

### 6.1 Test Suites Status
There are 2 existing test modules in `tests/`:
1. `tests/test_deployment.py`:
   - 12 test cases verifying production config precedence, health checks (`/health`, `/health/db`), error redaction, forecast horizon rejections, LINE HMAC signatures, and multi-channel alert fan-out (`NotificationFanOutTests`).
2. `tests/test_forecasting.py`:
   - 15 test cases verifying 500-day verified data quality gating, duplicate/null price rejection, walk-forward determinism, baseline fallback gates, forecast evaluation metrics, and BOT exchange parser.

### 6.2 Test Execution Result
Ran discovery using `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"`:
- **Total Tests**: 27
- **Passed**: 27 (100%)
- **Failed**: 0
- **Duration**: 5.04s

---

## 7. Strategic Implementation Gaps & Action Items for Implementation Agents

1. **Agent A & B (Forecasting Engine)**:
   - Current model only supports 1 and 7-day horizons (`SUPPORTED_HORIZONS = (1, 7)` in `forecast_models.py` and `period in (1, 7)` in `forecast_routes.py`). Must extend to support **30-day** forward projections.
   - Current model only projects Thai gold bar (`bar_sell`). Must add support for **World Spot Gold**.
   - Dual-agent adversarial debate engine (Agent A technical trend vs Agent B macro/FX) with > 3% discrepancy resolution and strict min-max bounds must be integrated into `services/forecast_service.py`.
2. **Agent C (Backend Security & Connection Pooling)**:
   - Add `DBUtils` connection pooling in `api/database/connection.py`.
   - Add `Flask-Limiter` on `/login`, `/register`, and sensitive endpoints.
   - Enforce immediate session revocation on password change (`DELETE FROM sessions WHERE user_id = ...`).
   - Complete migration of remaining legacy PHP endpoints to Flask (`forgot-password`, `reset-password`, `verify-email`).
3. **Agent D (Notifications & Auth Flow)**:
   - Implement `send_verification_email_smtp` and `send_password_reset_email_smtp` in `services/email_service.py`.
   - Wire up end-to-end token verification in `routes/auth_routes.py`.
   - Ensure multi-channel alert engine dispatches reliably without crashing on individual channel failures.
4. **Agent E (QA Test & Git Push)**:
   - Install and configure `pytest`.
   - Add test coverage for connection pooling, rate limiting, session invalidation on password change, 30-day forecast, and dual-agent debate.
   - Push verified commits to `DoubleFo20/gold-price-checker` on branch `main`.
