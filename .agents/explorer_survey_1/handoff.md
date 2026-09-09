# Handoff Report — Explorer Survey 1

**Agent**: `explorer_survey_1`  
**Timestamp**: 2026-09-09T15:46:00Z  
**Role**: Teamwork Explorer (Codebase survey, architecture & legacy migration analysis)  
**Deliverable Document**: `d:\xampp\htdocs\gold-price-checker\.agents\explorer_survey_1\survey_report.md`

---

## 1. Observation

1. **Environment and Dependencies**:
   - `.python-version`: specifies `3.11.9`.
   - `.venv`: exists at `d:\xampp\htdocs\gold-price-checker\.venv` containing Python 3.11.9.
   - `requirements.txt`: contains 16 packages (`flask`, `flask-cors`, `requests`, `beautifulsoup4`, `yfinance`, `scikit-learn`, `numpy`, `lxml`, `statsmodels`, `python-dotenv`, `pymysql>=1.1.0`, `cryptography>=41.0.0`, `bcrypt>=4.1.2`, `pywebpush>=2.0.3`, `gunicorn`, `waitress`).
   - Neither `Flask-Limiter`, `DBUtils`, nor `pytest` is currently installed in `.venv` or listed in `requirements.txt`.
   - No root `package.json` exists; frontend is vanilla HTML/JS/CSS.
   - Remote Git repository: `origin` points to `https://github.com/DoubleFo20/gold-price-checker.git` on branch `main`.
2. **Database Setup & Connection Handling**:
   - `api/sql/goldapidb.sql`: defines 17 canonical tables (`users`, `sessions`, `price_alerts`, `calculation_history`, `saved_forecasts`, `rate_limits`, `email_logs`, `price_cache`, `forecast_model_metrics`, `forecast_predictions`, `api_request_logs`, `auth_logs`, `cron_job_runs`, `activity_logs`, `notifications`, `email_verifications`, `password_resets`).
   - `api/database/connection.py`:
     ```python
     def get_db_connection():
         ...
         return pymysql.connect(
             host=host, user=user, password=password, database=database,
             port=port, cursorclass=pymysql.cursors.DictCursor, **connect_options
         )
     ```
     No connection pool exists; every call creates a new TCP socket connection.
3. **Legacy PHP Scripts Inventory**:
   - 48 PHP files exist across the workspace.
   - Several PHP scripts are broken due to missing files:
     - `api/api/auth/forgot.php`: line 4 requires `../../includes/email.php` (file does not exist).
     - `api/api/auth/resend_verify.php`: line 4 requires `../../includes/email.php` (file does not exist).
     - `api/api/proxy/historical.php`: line 3 requires `../../includes/rate_limit.php` (file does not exist).
     - `api/tools/test_email.php`: line 2 requires `../includes/email.php` (file does not exist).
   - Auth routes missing in Flask: `forgot.php`, `reset.php`, `verify.php`, `resend_verify.php`, `me.php`.
   - In Flask `api/routes/auth_routes.py` lines 186-189: `php_compat_change_password()` updates password hash, but never deletes from `sessions`, leaving existing session tokens active.
4. **Frontend API Call Inconsistencies**:
   - `js/config.js` lines 41-47:
     ```javascript
     const _phpApiBase = _isLocalhost && !_forceLocalApi ? "api/api" : `${_pythonApiUrl}/api/api`;
     ```
     Causes frontend on localhost to bypass Flask and call Apache/PHP directly unless `_forceLocalApi` or query string is set.
   - `js/script.js` directly calls `.php` endpoints (`login.php`, `register.php`, `forgot.php`, `check_session.php`, `logout.php`, `save_forecast.php`, `get_saved_forecasts.php`, `create.php`, `delete.php`, `list.php`).
5. **Existing Test Suite Execution**:
   - Ran `d:\xampp\htdocs\gold-price-checker\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"`:
     - `Ran 27 tests in 5.041s`
     - Result: `OK` (100% pass rate across 27 tests).

---

## 2. Logic Chain

1. **Premise**: Production stability requires connection reuse and resilience against high concurrency.
   - **Observation**: `api/database/connection.py:15-35` instantiates a new PyMySQL TCP connection per query.
   - **Deduction**: Connection pooling (via `DBUtils.pooled_db.PooledDB`) must be implemented to fulfill Requirement R3.
2. **Premise**: Password changes must immediately terminate unauthorized session access across devices.
   - **Observation**: `api/routes/auth_routes.py:166-197` executes only `UPDATE users SET password_hash=%s WHERE id=%s` and omits session revocation.
   - **Deduction**: Password update route must execute `DELETE FROM sessions WHERE user_id=%s` to satisfy Acceptance Criteria "Password updates immediately invalidate all prior active session tokens".
3. **Premise**: Email verification and password reset flows must function without external PHP/Apache dependencies.
   - **Observation**: PHP scripts (`forgot.php`, `resend_verify.php`) require missing include `email.php` and crash; Flask does not yet expose `/api/auth/forgot-password`, `/api/auth/reset-password`, or `/api/auth/verify-email`.
   - **Deduction**: Endpoints must be ported to Flask in `api/routes/auth_routes.py`, utilizing `api/services/email_service.py` with SMTP HTML templates.
4. **Premise**: All frontend API calls must route through the unified Flask service without legacy mode workarounds.
   - **Observation**: `js/config.js` branches on `_legacyLocalMode` and `_phpApiBase`.
   - **Deduction**: Unifying `js/config.js` on relative `/api/*` endpoints and aliasing legacy `.php` paths within Flask eliminates Apache dependency and standardizes the architecture.
5. **Premise**: Forecasting must support 7-day and 30-day horizons with dual-agent debate and strict bounds.
   - **Observation**: `api/routes/forecast_routes.py:25` hardcodes `if period not in (1, 7): return 400`, and `api/services/forecast_models.py:22` defines `SUPPORTED_HORIZONS = (1, 7)`.
   - **Deduction**: `SUPPORTED_HORIZONS` and route validation must be expanded to include 30-day forward forecasts, and dual-agent adversarial consensus must be integrated.

---

## 3. Caveats

- Neither Apache nor MySQL was actively running as a background service during this static inspection; tests were executed using unittest mocks and in-memory test doubles.
- The `price_cache` table requires historical data population (via `tools/import_gold_history.py`) for live statistical modeling beyond baseline fallback.
- Third-party external API keys (`LINE_CHANNEL_ACCESS_TOKEN`, `SMTP_PASS`, `NEWSAPI_KEY`) depend on `.env` configuration during live runtime deployment.

---

## 4. Conclusion

1. The project has a solid Python/Flask foundation in `api/` with 27 passing unit tests, but currently operates with single raw database connections, missing rate limiting, incomplete session revocation on password changes, and legacy `.php` URL routes.
2. The remaining legacy PHP scripts (48 files) can be safely deprecated: all critical core business logic (alerts, scheduled jobs, price scraping, admin panel) has already been ported to Python, with only the password-reset and email-verification flows left to finalize in Flask.
3. Frontend code in `js/config.js` and `js/script.js` can be cleanly decoupled from PHP by redirecting API calls to canonical `/api/*` endpoints while maintaining backwards-compatible route aliases in Flask.
4. Detailed findings, endpoint maps, and work package roadmaps for Agents A, B, C, D, and E are fully documented in `.agents/explorer_survey_1/survey_report.md`.

---

## 5. Verification Method

To verify the findings of this survey:
1. **Run Current Test Suite**:
   ```powershell
   & "d:\xampp\htdocs\gold-price-checker\.venv\Scripts\python.exe" -m unittest discover -s tests -p "test_*.py"
   ```
   *Expected output*: `Ran 27 tests in ... OK`.
2. **Inspect Connection Handling**:
   Check `d:\xampp\htdocs\gold-price-checker\api\database\connection.py` lines 15-35.
3. **Inspect Password Change Session Invalidation Gap**:
   Check `d:\xampp\htdocs\gold-price-checker\api\routes\auth_routes.py` lines 186-190.
4. **Inspect Missing Includes in PHP**:
   Check `d:\xampp\htdocs\gold-price-checker\api\api\auth\forgot.php` line 4 and confirm `api/includes/email.php` does not exist.
5. **Inspect Forecast Period Restrictions**:
   Check `d:\xampp\htdocs\gold-price-checker\api\routes\forecast_routes.py` line 25 and `api/services/forecast_models.py` line 22.
