# Handoff Report: Security, Auth, Notification Engine & Testing Survey

**Agent**: explorer_survey_3  
**Handoff Type**: Hard (Task Complete)  
**Target Requirements**: R2 (Notification & Alert System), R3 (Backend Security & DB Pooling), R4 (Testing & GitHub Sync)  
**Reference Report**: `d:\xampp\htdocs\gold-price-checker\.agents\explorer_survey_3\survey_report.md`  

---

## 1. Observation

### 1.1 Authentication & Session Management
- **File**: `d:\xampp\htdocs\gold-price-checker\api\routes\auth_routes.py`
  - Lines 38-82: `php_compat_login()` accepts email/password, checks `users WHERE email=%s AND is_active=1`, verifies bcrypt hash, generates 64-character token via `os.urandom(32).hex()`, and inserts into `sessions` with 7-day expiration (`expires_ts = int(time.time()) + (86400 * 7)`).
  - Lines 84-114: `php_compat_register()` inserts into `users` (`email, password_hash, name, role='user', is_active=1`), but creates no entry in `email_verifications` and does not send any verification email.
  - Lines 166-197: `php_compat_change_password()`:
    ```python
    186:         new_hash = _bcrypt_hash(new_password)
    187:         with conn.cursor() as cursor:
    188:             cursor.execute("UPDATE users SET password_hash=%s WHERE id=%s", (new_hash, user["id"]))
    189:         conn.commit()
    190:         return jsonify(success=True, message="เปลี่ยนรหัสผ่านสำเร็จ"), 200
    ```
    There is no query deleting or revoking records in the `sessions` table.
- **File**: `d:\xampp\htdocs\gold-price-checker\api\sql\goldapidb.sql`
  - Lines 350-370 define `email_verifications` (`id, user_id, token, expires_at, created_at`) and `password_resets` (`id, user_id, token, expires_at, created_at`).
  - No Flask routes exist for `/api/auth/verify-email`, `/api/auth/resend-verify`, `/api/auth/forgot-password`, or `/api/auth/reset-password`. Legacy PHP files `api/api/auth/forgot.php` and `api/api/auth/reset.php` fail due to missing `includes/email.php`.
- **Command & Tool Output**: `python -m pip list`
  - Output shows `Flask 3.1.3`, `bcrypt 5.0.0`, `PyMySQL 1.1.2`, `cryptography 48.0.0`, `pywebpush 2.3.0`.
  - `Flask-Limiter` is **NOT installed** in the environment.
  - `requirements.txt` contains 16 packages; `flask-limiter` is **NOT listed**.
  - `api/app/create_app.py` contains no `Limiter` instance or rate limiting configuration.

### 1.2 Database Connection & Pooling
- **File**: `d:\xampp\htdocs\gold-price-checker\api\database\connection.py`
  - Lines 15-36:
    ```python
    27:     return pymysql.connect(
    28:         host=host,
    29:         user=user,
    30:         password=password,
    31:         database=database,
    32:         port=port,
    33:         cursorclass=pymysql.cursors.DictCursor,
    34:         **connect_options,
    35:     )
    ```
  - Every call to `get_db_connection()` initiates an independent TCP connection to MySQL.
  - There is no pooling mechanism (no `DBUtils`, no connection queue, no persistent pool).

### 1.3 Notification Engine
- **LINE Messaging API & Webhook**:
  - `api/routes/webhook.py:14-107`: Handles `POST /webhook` and `GET /webhook`. Validates `X-Line-Signature` using `_line_signature_ok(body, signature)`.
  - Supports inbound commands `price`, `world`, `status`, `unlink`, and `LINK-XXXXXX` / `XXXXXX` for account linking.
  - `api/services/line_service.py:20-36`: `_line_push()` pushes text messages to `https://api.line.me/v2/bot/message/push` using Bearer `LINE_CHANNEL_ACCESS_TOKEN`.
- **SMTP Email Delivery**:
  - `api/services/email_service.py`: Dispatches emails via `_send_smtp()` using `smtplib.SMTP(cfg["host"], cfg["port"])` with STARTTLS.
  - Line 64: `send_alert_email_smtp(alert, current_price)` sends price alert emails.
  - Line 143: `send_forecast_result_email_smtp(payload)` sends forecast verification emails.
  - **Omission**: `_send_smtp()` never writes records to the `email_logs` table (`api/sql/goldapidb.sql:169-186`).
  - **Omission**: No functions exist to send email verification or password reset emails.
  - **Omission**: No scheduled morning price summary notification exists in `api/services/scheduler.py`.
- **Web Push Service Worker**:
  - Root `sw.js` (lines 1-28):
    ```javascript
    2: self.addEventListener('push', function(event) {
    3:     if (event.data) {
    4:         const data = event.data.json();
    ...
    17:         event.waitUntil(
    18:             self.registration.showNotification(data.title, options)
    19:         );
    20:     }
    21: });
    ```
  - `event.data.json()` lacks try-catch error handling.
  - `notificationclick` calls `clients.openWindow(event.notification.data.url)` without window reuse.

### 1.4 Testing Infrastructure & Git Status
- **Test Discovery**:
  - `python -m unittest discover -s tests -v` runs 27 tests in `tests/test_deployment.py` and `tests/test_forecasting.py`.
  - Output: `Ran 27 tests in 13.090s - OK`. All 27 tests pass.
  - `pytest --version` output: `pytest : The term 'pytest' is not recognized as the name of a cmdlet, function, script file, or operable program.`
- **Git Status**:
  - `git status` output: `On branch main. Your branch is up to date with 'origin/main'.`
  - `git remote -v`: `origin https://github.com/DoubleFo20/gold-price-checker.git (fetch & push)`.
  - `git fetch --dry-run`: Exits with code 0 (authenticated remote connectivity confirmed).

---

## 2. Logic Chain

1. **Password Change & Active Sessions**:
   - Observation: `php_compat_change_password` only updates `users.password_hash` (`auth_routes.py:188`) and does not modify `sessions`.
   - Observation: `_auth_get_user_by_session` queries `sessions s INNER JOIN users u` where `s.token = %s AND s.expires_at > NOW()` (`auth.py:12-16`).
   - Inference: Existing session tokens remain valid after password change for up to 7 days, allowing compromised tokens to continue accessing the account.
   - Conclusion: Violates Requirement R3 and Acceptance Criteria ("Password updates immediately invalidate all prior active session tokens for that user").

2. **Brute Force & Rate Limiting**:
   - Observation: `Flask-Limiter` is not installed, not in `requirements.txt`, and not used in `create_app.py`.
   - Inference: An attacker can send unlimited POST requests to `/api/api/auth/login.php` or `/api/api/auth/register.php`.
   - Conclusion: Rate limiting must be implemented in Flask using `Flask-Limiter` with strict limits on auth routes to satisfy Requirement R3.

3. **Database Scalability & Connection Pooling**:
   - Observation: Every request executes `pymysql.connect(...)` (`connection.py:27`).
   - Observation: Background jobs run every 60 seconds and create multiple connections.
   - Inference: Under concurrent multi-user load, high latency from connection setup and socket exhaustion (MySQL error 1040) will occur.
   - Conclusion: Integrating `DBUtils.pooled_db.PooledDB` into `connection.py` will establish a connection pool while preserving the `DictCursor` interface.

4. **Email Delivery Tracking & Auth Flow Gaps**:
   - Observation: `email_logs` table exists in SQL schema, but `email_service.py` never inserts into it.
   - Observation: Password reset and email verification tables exist, but no Flask endpoints or email templates handle them.
   - Conclusion: Requirement R2 and R3 require implementing email delivery logging, forgot/reset password routes, email verification routes, and HTML templates.

5. **Test Runner Compliance**:
   - Observation: Requirement R4 states "Execute comprehensive test suites (pytest)".
   - Observation: `pytest` is not installed; running `pytest` fails. Current tests run only under `unittest`.
   - Conclusion: `pytest` must be installed and added to `requirements.txt`, and additional test suites covering auth, rate limiting, and connection pooling must be added.

---

## 3. Caveats

1. **Live External Services**: LINE Messaging API tokens, Gmail SMTP credentials, and VAPID keys were verified structurally and configuration-wise via mock/unit tests (`tests/test_deployment.py:NotificationFanOutTests`), but real live external network dispatches require valid credentials in production `.env`.
2. **Database Schema in Remote Deployment**: The current schema in `api/sql/goldapidb.sql` contains definitions for all required tables (`rate_limits`, `email_logs`, `email_verifications`, `password_resets`), but the live deployed database instance must have these tables migrated if not already present.
3. **No Code Modification**: In accordance with the read-only boundary of this investigation, no code or package changes were made.

---

## 4. Conclusion

The system has a solid architectural foundation (Flask application factory, dual-agent forecasting scaffolding, working LINE webhook, VAPID web push backend, and 27 passing deployment/forecasting tests). However, critical gaps must be addressed to reach 100% production readiness:
1. **Security**: Add `Flask-Limiter` for auth endpoint throttling and enforce immediate revocation of all user sessions upon password change (`DELETE FROM sessions WHERE user_id=%s`).
2. **Database**: Implement `DBUtils.pooled_db.PooledDB` connection pooling in `api/database/connection.py`.
3. **Auth & Notifications**: Build Flask endpoints for password reset and email verification, log email dispatches to `email_logs`, add daily morning price summary notifications, and harden `sw.js` with try-catch and tab focus.
4. **Testing & Sync**: Install and configure `pytest`, add tests for security and notifications, and maintain automated synchronization to `origin/main`.

---

## 5. Verification Method

To independently verify all observations and conclusions in this report:

1. **Verify Test Suite & Missing Pytest**:
   ```powershell
   python -m unittest discover -s tests -v
   # (Expected: 27 passed tests)

   pytest --version
   # (Expected: command not found / ObjectNotFound)
   ```

2. **Verify Missing Flask-Limiter**:
   ```powershell
   python -m pip list | Select-String "limiter"
   # (Expected: empty output)
   ```

3. **Verify Git Remote Status**:
   ```powershell
   git status
   git remote -v
   git fetch --dry-run
   # (Expected: clean on main, up to date with DoubleFo20/gold-price-checker.git)
   ```

4. **Verify Session Invalidation Vulnerability in Code**:
   Inspect `api/routes/auth_routes.py` lines 166-197 to verify that `DELETE FROM sessions WHERE user_id=%s` is missing.

5. **Verify Database Connection Lack of Pooling**:
   Inspect `api/database/connection.py` lines 15-36 to verify direct `pymysql.connect` without pooling wrapper.

6. **Verify Email Tracking Lack of Logging**:
   Inspect `api/services/email_service.py` lines 20-47 to verify absence of `INSERT INTO email_logs`.
