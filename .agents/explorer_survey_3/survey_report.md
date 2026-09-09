# Comprehensive Survey Report: Security, Auth, Notification Engine, and Testing Infrastructure

**Author**: explorer_survey_3  
**Date**: 2026-09-09T15:45:00Z  
**Target Requirements**: R2 (Notification Engine), R3 (Backend Security & DB Pooling), R4 (Testing & CI/CD Git Sync)  
**Workspace Root**: `d:\xampp\htdocs\gold-price-checker`  

---

## Executive Summary

Explorer Survey 3 has conducted an exhaustive, read-only architectural investigation into the security, authentication, notification engine, database connection management, and testing infrastructure of the Gold Price Checker platform.

### Summary of Core Findings:
1. **Authentication & Session Security (Requirement R3)**:
   - **Critical Vulnerability**: In `api/routes/auth_routes.py:166-197` (`php_compat_change_password`), updating a password modifies `password_hash` in `users` but does **NOT** invalidate active session tokens in the `sessions` table. All prior active sessions remain valid for up to 7 days, directly violating Requirement R3 and Acceptance Criteria.
   - **Rate Limiting Absent**: `Flask-Limiter` is **not installed** in the virtual environment and **not present** in `requirements.txt`. Zero rate limiting exists on `/login`, `/register`, or password changes, exposing the backend to brute-force credential stuffing.
   - **Missing Modern Auth Flows**: Email verification (`email_verifications` table) and password reset (`password_resets` table) exist only in orphaned legacy PHP scripts (`api/api/auth/forgot.php`, `reset.php`, `verify.php`, `resend_verify.php`). Flask does not implement these routes.
   - **Legacy PHP-Compat Paths**: Existing Flask endpoints are mapped to legacy PHP-compatible paths (`/api/api/auth/login.php`, `/api/api/auth/register.php`). Clean REST endpoints (`/api/auth/login`, `/api/auth/register`, `/api/auth/forgot-password`, `/api/auth/reset-password`, `/api/auth/verify-email`) must be added as standardized routes.

2. **Database Connection Pooling (Requirement R3)**:
   - `api/database/connection.py:15-36` executes `pymysql.connect(...)` for every incoming HTTP request and background task. There is **no connection pool**.
   - Under concurrent user traffic and the 60-second background checker loop, this architecture incurs high TCP/TLS handshake latency and risks MySQL `Too many connections` errors.
   - A thread-safe connection pool using `DBUtils.pooled_db.PooledDB` wrapping PyMySQL is needed, maintaining full backward compatibility with the `pymysql.cursors.DictCursor` interface expected by all route handlers.

3. **Notification Engine (Requirement R2)**:
   - **LINE Messaging API**: Implemented in `api/services/line_service.py` and `api/routes/webhook.py` (`POST /webhook`). Verified HMAC-SHA256 signature verification (`X-Line-Signature`), inbound commands (price checks, account linking with 6-digit verification code), and outbound pushes via LINE Push Message API.
   - **SMTP Email Service**: Implemented in `api/services/email_service.py`. Successfully dispatches price alert emails and forecast verification summaries. **Deficiencies**: Does not write to `email_logs` table (delivery tracking missing, violating R2), lacks HTML templates and dispatchers for email verification/password resets, and does not provide scheduled daily morning price summary emails.
   - **Web Push Service Worker (`sw.js`)**: Root `sw.js` listens to push events and notification clicks. **Deficiencies**: Lacks resilient error handling around `event.data.json()`, does not reuse open tabs on `notificationclick`, and has no fallback payload handler.

4. **Testing & GitHub Sync (Requirement R4)**:
   - 27 unit tests currently exist in `tests/test_deployment.py` and `tests/test_forecasting.py`, all passing (100%) via `python -m unittest`.
   - `pytest` is **not installed** in the virtual environment and not in `requirements.txt`.
   - Critical test gaps: No test coverage for auth endpoints, session revocation, rate limiting, password reset/email verification, email delivery logging, or connection pool stress/reuse.
   - Git remote `origin` is confirmed connected to `https://github.com/DoubleFo20/gold-price-checker.git` on branch `main` with authenticated access.

---

## 1. Authentication, Sessions & Security (Requirement R3)

### 1.1 Detailed Endpoint Audit

The current authentication endpoints are located in `api/routes/auth_routes.py` and registered via `auth_bp = Blueprint("auth", __name__)`:

| Endpoint | Method | Function | Code Reference | Description & Vulnerabilities |
|---|---|---|---|---|
| `/api/api/auth/login.php` | POST, OPTIONS | `php_compat_login` | `auth_routes.py:38-82` | Authenticates via `SELECT * FROM users WHERE email=%s AND is_active=1`. Verifies bcrypt hash. Issues a 64-char token (`os.urandom(32).hex()`) valid for 7 days (`time.time() + 86400 * 7`). Inserts into `sessions (user_id, token, expires_at, ip_address, user_agent)`. Sets HTTP-only Lax cookie `session_token`. |
| `/api/api/auth/register.php` | POST, OPTIONS | `php_compat_register` | `auth_routes.py:84-114` | Validates email, password (length >= 6), and name. Hashes password using bcrypt. Inserts user into `users` with `is_active=1` and `role='user'`. **Bug/Omission**: Does NOT create an email verification token, does not set `is_verified=0` explicitly or trigger verification email. |
| `/api/api/auth/check_session.php` | POST, OPTIONS | `php_compat_check_session` | `auth_routes.py:116-136` | Reads cookie `session_token`. Validates session via `_auth_get_user_by_session(conn, token)` (`services/auth.py:6-20`). Returns authenticated user info. |
| `/api/api/auth/update_profile.php` | POST, OPTIONS | `php_compat_update_profile` | `auth_routes.py:138-164` | Requires authenticated session. Updates `name` column in `users`. |
| `/api/api/auth/change_password.php` | POST, OPTIONS | `php_compat_change_password` | `auth_routes.py:166-197` | Requires authenticated session. Verifies `old_password` against database hash, updates `password_hash` with `new_password`. **CRITICAL SECURITY FLAW**: Fails to delete existing session tokens from `sessions` table! |
| `/api/api/auth/logout.php` | POST, OPTIONS | `php_compat_logout` | `auth_routes.py:199-222` | Deletes the caller's active session token: `DELETE FROM sessions WHERE token=%s`. |
| `/api/debug/db` | GET | `debug_db` | `auth_routes.py:19-36` | Tests DB connectivity (`SELECT 1`). Properly disabled in production (`abort(404)`). |

### 1.2 Session Invalidation Analysis
- **Code Observation**: In `api/routes/auth_routes.py`, lines 186-190:
  ```python
  new_hash = _bcrypt_hash(new_password)
  with conn.cursor() as cursor:
      cursor.execute("UPDATE users SET password_hash=%s WHERE id=%s", (new_hash, user["id"]))
  conn.commit()
  return jsonify(success=True, message="เปลี่ยนรหัสผ่านสำเร็จ"), 200
  ```
- **Vulnerability**: If an attacker or compromised device holds an active session token, changing the password does nothing to terminate that session. The attacker maintains full authenticated access until the 7-day cookie expires.
- **Requirement Violation**: R3 explicitly requires:
  *"Ensure changing passwords immediately revokes all existing active session tokens in the database."*
  Acceptance Criteria:
  *"Password updates immediately invalidate all prior active session tokens for that user."*
- **Remediation**:
  In `change_password`, immediately execute:
  ```python
  cursor.execute("DELETE FROM sessions WHERE user_id=%s", (user["id"],))
  ```
  And either require immediate re-login, or generate a fresh new session token and attach it to the response cookie.

### 1.3 Rate Limiting Status (Flask-Limiter)
- **Status**: Completely absent.
  - Virtual environment check: `python -m pip list` confirms `Flask-Limiter` is not installed.
  - Dependency manifest check: `requirements.txt` does not include `flask-limiter`.
  - Application factory check: `api/app/create_app.py` has zero rate limiting configuration or hooks.
- **Impact**: Auth routes can be brute-forced without limitation.
- **Remediation**:
  1. Add `Flask-Limiter>=3.5.0` to `requirements.txt`.
  2. In `api/app/create_app.py`, initialize:
     ```python
     from flask_limiter import Limiter
     from flask_limiter.util import get_remote_address

     limiter = Limiter(
         key_func=get_remote_address,
         default_limits=["200 per day", "50 per hour"],
         storage_uri="memory://",
     )
     limiter.init_app(app)
     ```
  3. Apply decorators to sensitive endpoints:
     - `@limiter.limit("5 per minute")` on `/api/api/auth/login.php` and `/api/auth/login`
     - `@limiter.limit("3 per minute")` on `/api/api/auth/register.php` and `/api/auth/register`
     - `@limiter.limit("3 per minute")` on `/api/auth/forgot-password` and `/api/auth/reset-password`

### 1.4 Missing Auth Flows (Email Verification & Password Reset)
- **Database Schema Support**:
  `api/sql/goldapidb.sql` lines 351-370 defines:
  ```sql
  CREATE TABLE IF NOT EXISTS email_verifications (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    user_id INT UNSIGNED NOT NULL,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_expires (user_id, expires_at)
  );

  CREATE TABLE IF NOT EXISTS password_resets (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    user_id INT UNSIGNED NOT NULL,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_expires (user_id, expires_at)
  );
  ```
- **State in Legacy PHP**:
  - `api/api/auth/forgot.php`: Inserts into `password_resets`, calls `sendPasswordResetEmail` (broken dependency on non-existent `includes/email.php`).
  - `api/api/auth/reset.php`: Validates token from `password_resets`, updates `users.password_hash`, deletes reset token.
  - `api/api/auth/verify.php`: Validates token from `email_verifications`, updates `users.is_verified=1`, deletes token.
  - `api/api/auth/resend_verify.php`: Inserts token into `email_verifications`, calls `sendVerificationEmail`.
- **State in Python Flask**: Zero implementation. These endpoints are completely missing from Flask route definitions.
- **Frontend References**: `js/script.js:219` attempts `fetch("${window.APP_CONFIG.PHP_API_BASE}/auth/forgot.php")`.

---

## 2. Database Connection Management & Connection Pooling (Requirement R3)

### 2.1 Current Implementation Inspection (`api/database/connection.py`)
```python
def get_db_connection():
    host = os.getenv("DB_HOST")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    database = os.getenv("DB_NAME")
    port = int(os.getenv("DB_PORT", 3306))

    connect_options = {}
    ssl_ca = (os.getenv("DB_SSL_CA") or "").strip()
    if ssl_ca:
        connect_options["ssl"] = {"ca": ssl_ca, "check_hostname": True}

    return pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port,
        cursorclass=pymysql.cursors.DictCursor,
        **connect_options,
    )
```
### 2.2 Operational Deficiencies
1. **Connection Lifecycle Inefficiency**: Every single API request opens a distinct TCP socket to MySQL, conducts full SSL/TLS handshaking (especially slow on remote managed DBs like Aiven MySQL), executes queries, and terminates the socket with `conn.close()`.
2. **Background Thread Contention**: In `api/scheduler/jobs.py`, the background thread calls `run_scheduled_jobs_once()` every 60 seconds, which opens and closes multiple database connections in sequence (`save_daily_price`, `alerts`, `forecasts`).
3. **Connection Spikes**: Under high concurrency or network latency, MySQL connection limits (`max_connections`) can quickly be exhausted, resulting in HTTP 503 errors.

### 2.3 Required Connection Pool Architecture
- **Library**: `DBUtils` (specifically `dbutils.pooled_db.PooledDB`).
- **Compatibility Constraint**: The platform relies extensively on dictionary cursors: `cursorclass=pymysql.cursors.DictCursor` across all route handlers and services (`routes/alerts.py`, `routes/user_routes.py`, `routes/admin.py`, `services/scheduler.py`).
- **Implementation Plan**:
  ```python
  from dbutils.pooled_db import PooledDB
  import pymysql

  _pool = None

  def get_pool():
      global _pool
      if _pool is None:
          connect_options = {}
          ssl_ca = (os.getenv("DB_SSL_CA") or "").strip()
          if ssl_ca:
              connect_options["ssl"] = {"ca": ssl_ca, "check_hostname": True}
          _pool = PooledDB(
              creator=pymysql,
              mincached=int(os.getenv("DB_POOL_MIN", 2)),
              maxcached=int(os.getenv("DB_POOL_MAX", 10)),
              maxconnections=int(os.getenv("DB_POOL_LIMIT", 20)),
              blocking=True,
              ping=1,  # Pings MySQL on checkout; reconnects if server closed socket
              host=os.getenv("DB_HOST"),
              user=os.getenv("DB_USER"),
              password=os.getenv("DB_PASSWORD"),
              database=os.getenv("DB_NAME"),
              port=int(os.getenv("DB_PORT", 3306)),
              cursorclass=pymysql.cursors.DictCursor,
              **connect_options,
          )
      return _pool

  def get_db_connection():
      pool = get_pool()
      return pool.connection()
  ```
- **Transparent Drop-in**: When callers call `conn = get_db_connection()` and then `conn.close()`, `PooledDB`'s pooled connection proxy intercepts `close()` and returns the connection to the pool rather than severing the TCP socket. Zero refactoring required for existing query callers!

---

## 3. Notification & Alert Engine (Requirement R2)

### 3.1 LINE Messaging API & Webhook
- **Webhook Implementation**: `api/routes/webhook.py` (`POST /webhook`).
- **Signature Security**:
  - `_line_signature_ok(body, signature)` in `api/services/line_service.py:112-119` validates `X-Line-Signature` using `LINE_CHANNEL_SECRET` and HMAC-SHA256 with constant-time comparison `hmac.compare_digest`.
  - Comprehensive unit tests exist in `tests/test_deployment.py:108-134` verifying rejection of missing or invalid signatures and acceptance of valid signatures.
- **Inbound Message Flow**:
  - `price` / `ราคา` -> calls `_line_get_cached_prices_text("all")`, returning gold bar buy/sell and ornament prices.
  - `world` / `ราคาทองโลก` -> replies with XAU/USD gold spot price.
  - `status` / `สถานะ` -> queries user linking status from DB.
  - `LINK-XXXXXX` / `XXXXXX` -> looks up `users.verification_token = %s`, links `line_user_id` and `line_display_name`, and clears `verification_token`.
  - `unlink` / `ยกเลิก` -> clears `line_user_id` and `line_display_name`.
- **Outbound Message Flow**:
  - `_line_push(line_user_id, text)` in `api/services/line_service.py:20-36` dispatches to `https://api.line.me/v2/bot/message/push` with Bearer token authentication.
  - Price alert triggers in `services/notification.py:_deliver_price_alert` successfully format Thai messages and invoke `_line_push`.

### 3.2 SMTP Email Delivery & Tracking Deficiencies
- **Implementation**: `api/services/email_service.py`.
- **Existing Mailers**:
  - `send_alert_email_smtp(alert, current_price)` (`email_service.py:49-90`): Formats HTML and plaintext alerts for gold bar, ornament, and world spot price condition breaches.
  - `send_forecast_email_smtp(payload)` (`email_service.py:92-141`): Summarizes user-saved gold forecast predictions.
  - `send_forecast_result_email_smtp(payload)` (`email_service.py:143-185`): Notifies user when target date is reached with actual vs forecast comparison.
- **Critical Gaps vs Requirement R2**:
  1. **Delivery Tracking**: Requirement R2 specifies *"HTML SMTP Email alerts with verification and delivery tracking"*. Table `email_logs` exists in `api/sql/goldapidb.sql:169-186`:
     ```sql
     CREATE TABLE IF NOT EXISTS email_logs (
       id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
       user_id INT UNSIGNED NULL,
       recipient_email VARCHAR(255) NOT NULL,
       subject VARCHAR(255),
       status ENUM('sent','failed') NOT NULL,
       error_message TEXT NULL,
       sent_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
       KEY idx_email_user_date (user_id, sent_at),
       KEY idx_email_status_date (status, sent_at),
       KEY idx_email_recipient (recipient_email)
     );
     ```
     `_send_smtp` does **NOT** log into `email_logs`. All dispatch attempts pass or fail silently without audit trail.
  2. **Auth Email Templates**: No email verification or password reset email dispatchers exist in `email_service.py`.
  3. **Daily Morning Price Summary**: Requirement R2 requires *"scheduled notifications for daily morning price summaries"*. Currently, `scheduler.py:save_daily_price` only updates `price_cache` without triggering any summary notification broadcast.

### 3.3 Web Push Service Worker (`sw.js`)
- **Location**: Root `/sw.js` (28 lines).
- **Service Worker Code**:
  ```javascript
  self.addEventListener('push', function(event) {
      if (event.data) {
          const data = event.data.json();
          const defaultUrl = new URL(self.registration.scope).pathname || '/';
          const options = {
              body: data.body,
              data: { url: data.url || defaultUrl }
          };
          if (data.icon) options.icon = data.icon;
          if (data.badge) options.badge = data.badge;
          event.waitUntil(self.registration.showNotification(data.title, options));
      }
  });

  self.addEventListener('notificationclick', function(event) {
      event.notification.close();
      event.waitUntil(clients.openWindow(event.notification.data.url));
  });
  ```
- **Deficiencies & Hardening Requirements**:
  1. **Exception Safety in Push Event**: If payload is not valid JSON, `event.data.json()` throws an unhandled SyntaxError and drops the notification. Must wrap in try-catch with `event.data.text()` fallback.
  2. **Window Matching on Click**: `clients.openWindow(...)` opens duplicate tabs on every click. Must use `clients.matchAll({ type: 'window', includeUncontrolled: true })` and focus an existing app tab if open.
  3. **Vibration & Tagging**: Add `tag: 'gold-price-alert'`, `renotify: true`, and standard vibration patterns for price alerts.
- **Backend Web Push Integration**:
  - `services/notification.py:_send_web_push` uses `pywebpush` with VAPID keys (`VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`).
  - Key distribution endpoint: `GET /api/web-push/public-key` in `api/routes/jobs.py:37-41`.
  - Frontend subscription flow in `js/script.js:1855-1980` registers `sw.js` and calls `api/api/profile/update_push.php` (which stores subscription JSON in `users.push_subscription`).

---

## 4. Testing Infrastructure & Git Synchronization (Requirement R4)

### 4.1 Current Test Suite Status
- **Test Discovery & Execution**:
  - Discovery path: `tests/`
  - Existing test files:
    - `tests/test_deployment.py` (Production config, health endpoints, DB readiness, IP normalization, LINE webhook signatures, multi-channel alert fan-out, DB TLS connection).
    - `tests/test_forecasting.py` (Data quality, observation threshold, continuity gaps, walk-forward evaluation, baseline vs champion, contract backtest metrics).
  - Test command: `python -m unittest discover -s tests -v`
  - Test results: **27 passed in 13.090s (0 failures, 0 errors)**.
- **Testing Infrastructure Deficiencies**:
  1. **Missing `pytest`**: Requirement R4 explicitly requires automated test suites run with `pytest`. `pytest` is not installed in `.venv` and not declared in `requirements.txt`.
  2. **Missing Test Coverage**:
     - Zero tests for login rate limiting and brute-force throttling.
     - Zero tests for immediate session invalidation upon password update.
     - Zero tests for password reset token creation, expiration, and password override.
     - Zero tests for email verification token validation.
     - Zero tests for database connection pooling checkout, reuse, and exhaustion handling.
     - Zero tests for `email_logs` delivery tracking insertion.

### 4.2 Git Status & Remote Repository Synchronization
- **Repository Remote**: `origin` -> `https://github.com/DoubleFo20/gold-price-checker.git`
- **Active Branch**: `main`
- **Sync Status**: `Your branch is up to date with 'origin/main'`
- **Connectivity Check**: `git fetch --dry-run` successfully completed with exit code 0.
- **Working Tree State**:
  - Modified: `js/config.js` (clean quote normalization).
  - Untracked: `.agents/` and `ORIGINAL_REQUEST.md`.

---

## 5. Recommended Action Plan & Work Breakdown

### Work Package for Agent C (Backend Security & Database Architecture):
1. **DB Connection Pooling**:
   - Add `DBUtils` to `requirements.txt`.
   - Implement `PooledDB` singleton in `api/database/connection.py` with `mincached=2, maxcached=10, maxconnections=20, ping=1`.
2. **Rate Limiting**:
   - Add `flask-limiter` to `requirements.txt`.
   - Instantiate `Limiter` in `api/app/create_app.py` and apply to `/login` (5/min), `/register` (3/min), and `/change_password`.
3. **Session Invalidation**:
   - In `api/routes/auth_routes.py:php_compat_change_password`, execute `DELETE FROM sessions WHERE user_id=%s` on password change.
4. **Standardize API Routes**:
   - Provide standard REST paths (`/api/auth/login`, `/api/auth/register`, `/api/auth/logout`, `/api/auth/change-password`) while maintaining backward-compatible `/api/api/auth/*.php` aliases.

### Work Package for Agent D (Notifications & Auth Flow Champion):
1. **Email Verification & Password Reset**:
   - Add `/api/auth/forgot-password` and `/api/auth/reset-password` in Flask.
   - Add `/api/auth/verify-email` and `/api/auth/resend-verify` in Flask.
   - Design and build responsive HTML email templates for token verification and password reset.
2. **Email Delivery Tracking**:
   - Update `email_service.py:_send_smtp` to insert log records into `email_logs` (`recipient_email`, `subject`, `status`, `error_message`, `sent_at`).
3. **Daily Morning Price Summary**:
   - Add scheduled morning gold price broadcast job in `scheduler.py` (LINE push & email summary).
4. **Harden `sw.js`**:
   - Add try-catch fallback handling for push event data and tab-reuse focus on notification click.

### Work Package for Agent E (QA Test & GitHub Pusher):
1. **Pytest Setup**:
   - Add `pytest` and `pytest-cov` to `requirements.txt` and install into `.venv`.
   - Add `pytest.ini` for standardized test runner configuration.
2. **New Test Suites**:
   - `tests/test_auth_security.py`: Test rate limiting, password reset expiration, and session revocation on password change.
   - `tests/test_notifications.py`: Test `email_logs` recording on mail dispatch.
   - `tests/test_db_pool.py`: Test concurrent checkout and connection reuse.
3. **Verification & Sync**:
   - Execute full test suite via `pytest`.
   - Push verified milestone commits to `origin/main`.
