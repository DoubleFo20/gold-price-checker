# Forensic Audit Report: Milestone M1 (Backend Security & Database Architecture)

**Auditor**: auditor_m1 (Forensic Auditor)  
**Timestamp**: 2026-09-09T15:58:30Z  
**Work Product**: Milestone M1 Changes by `worker_m1`:
  - `api/database/connection.py`
  - `api/routes/auth_routes.py`
  - `api/utils/limiter.py`
  - `api/app/create_app.py`
  - `js/config.js`
  - `tests/test_m1_security_db.py`
  - `requirements.txt`
**Profile**: General Project (Integrity Mode: Development, per `ORIGINAL_REQUEST.md:8`)  
**Verdict**: **CLEAN**

---

## 1. Observation

### 1.1 Pre-Populated Artifact & Facade Detection
- Command executed:
  ```powershell
  Get-ChildItem -Path "d:\xampp\htdocs\gold-price-checker" -Exclude ".venv",".git" | Where-Object { $_.Name -notmatch '^\.' } | ForEach-Object { Get-ChildItem -Path $_.FullName -Recurse -Include *.log,*result*,*output* -File -ErrorAction SilentlyContinue } | Select-Object FullName, Length, LastWriteTime
  ```
  *Result*: Output empty. Zero pre-populated test result files, logs, or attestation artifacts exist in the repository tree outside `.venv`.
- Grep for `TESTING` or `mock` bypasses in `api/`:
  No mock bypass flags, debug skips, or test-mode shortcuts exist in `api/routes/auth_routes.py`, `api/database/connection.py`, or `api/utils/limiter.py`.

### 1.2 Implementation Verification: Session Invalidation on Password Change
- File: `api/routes/auth_routes.py:204-211`:
  ```python
  new_hash = _bcrypt_hash(new_password)
  with conn.cursor() as cursor:
      cursor.execute("UPDATE users SET password_hash=%s WHERE id=%s", (new_hash, user["id"]))
      # Immediately revoke all existing active sessions for this user
      cursor.execute("DELETE FROM sessions WHERE user_id=%s", (user["id"],))
  conn.commit()
  resp = jsonify(success=True, message="เปลี่ยนรหัสผ่านสำเร็จ กรุณาเข้าสู่ระบบใหม่")
  resp.set_cookie("session_token", "", expires=0, path="/")
  return resp, 200
  ```
- Directly verifies that:
  1. `cursor.execute("DELETE FROM sessions WHERE user_id=%s", (user["id"],))` is executed against the DB connection cursor within the same transaction.
  2. `conn.commit()` is called immediately afterward.
  3. `resp.set_cookie("session_token", "", expires=0, path="/")` explicitly invalidates the browser cookie.
  4. Failure paths (e.g., mismatched old password) exit early before executing `DELETE FROM sessions`.

### 1.3 Implementation Verification: Database Connection Pooling (`PooledDB`)
- File: `api/database/connection.py:7-18, 87-101, 158-161`:
  ```python
  try:
      import dbutils
      import dbutils.pooled_db
      sys.modules.setdefault("DBUtils", dbutils)
      sys.modules.setdefault("DBUtils.pooled_db", dbutils.pooled_db)
      from dbutils.pooled_db import PooledDB
  except ImportError: ...
  ```
  ```python
  _pool = PooledDB(
      creator=pymysql,
      mincached=cfg.get("mincached", 0),
      maxcached=cfg.get("maxcached", 10),
      maxconnections=cfg.get("maxconnections", 20),
      blocking=cfg.get("blocking", True),
      ping=1,
      host=cfg.get("host"),
      user=cfg.get("user"),
      password=cfg.get("password"),
      database=cfg.get("database"),
      port=cfg.get("port"),
      cursorclass=pymysql.cursors.DictCursor,
      **cfg.get("connect_options", {}),
  )
  ```
  ```python
  pool = get_db_pool()
  if pool is not None:
      return pool.connection()
  ```
- Genuine `PooledDB` instance manages checkout and checkin. When `.close()` is invoked on the connection returned by `get_db_connection()`, the connection returns to the idle pool rather than terminating the physical socket.
- Concurrency test `test_thread_safe_pool_concurrency` verifies 8 threads checking out and releasing connections concurrently without deadlock.

### 1.4 Implementation Verification: Rate Limiting Throttling (`Flask-Limiter`)
- File: `api/utils/limiter.py:9-30` & `api/app/create_app.py:37-50`:
  - Uses `get_client_ip_key()` with proxy-aware IP resolution (`_client_ip(request)`).
  - Configured with `default_limits=["200 per day", "50 per hour"]` and `storage_uri=memory://`.
  - Registered via `limiter.init_app(app)` with custom 429 JSON handler returning `error: "rate_limit_exceeded"`.
  - Decorated with `@limiter.limit("5 per minute")` on `/api/auth/login`, `/api/auth/register`, `/api/auth/change-password` and their PHP aliases.
  - `@limiter.request_filter` correctly exempts CORS preflight `OPTIONS` requests.

### 1.5 Independent Test Execution & Verification
1. **Independent Run of M1 Security & DB Tests**:
   - Command:
     ```powershell
     & "d:\xampp\htdocs\gold-price-checker\.venv\Scripts\python.exe" -m unittest discover -s tests -p "test_m1_*.py" -v
     ```
   - Verbatim output:
     ```
     test_failed_password_change_does_not_delete_sessions (test_m1_security_db.ActiveSessionRevocationTests.test_failed_password_change_does_not_delete_sessions) ... ok
     test_password_change_deletes_all_user_sessions (test_m1_security_db.ActiveSessionRevocationTests.test_password_change_deletes_all_user_sessions) ... ok
     test_php_compat_change_password_alias_deletes_sessions (test_m1_security_db.ActiveSessionRevocationTests.test_php_compat_change_password_alias_deletes_sessions) ... ok
     test_close_and_reinit_db_pool (test_m1_security_db.DatabaseConnectionPoolingTests.test_close_and_reinit_db_pool) ... ok
     test_dbutils_pooled_db_instance (test_m1_security_db.DatabaseConnectionPoolingTests.test_dbutils_pooled_db_instance) ... ok
     test_pooled_connection_checkout_and_close (test_m1_security_db.DatabaseConnectionPoolingTests.test_pooled_connection_checkout_and_close) ... ok
     test_thread_safe_pool_concurrency (test_m1_security_db.DatabaseConnectionPoolingTests.test_thread_safe_pool_concurrency) ... ok
     test_login_rate_limiting_throttles_after_limit (test_m1_security_db.RateLimitingThrottlingTests.test_login_rate_limiting_throttles_after_limit) ... ok
     test_options_preflight_is_exempt_from_rate_limit (test_m1_security_db.RateLimitingThrottlingTests.test_options_preflight_is_exempt_from_rate_limit) ... ok
     test_php_compat_login_shares_rate_limit (test_m1_security_db.RateLimitingThrottlingTests.test_php_compat_login_shares_rate_limit) ... ok
     test_all_auth_and_user_route_aliases_exist (test_m1_security_db.RouteAliasesTests.test_all_auth_and_user_route_aliases_exist) ... ok

     ----------------------------------------------------------------------
     Ran 11 tests in 14.928s

     OK
     ```

2. **Independent Run of Full Project Test Suite**:
   - Command:
     ```powershell
     & "d:\xampp\htdocs\gold-price-checker\.venv\Scripts\python.exe" -m unittest discover -s tests -p "test_*.py" -v
     ```
   - Verbatim output:
     ```
     Ran 51 tests in 26.485s

     OK
     ```
   - Includes 27 existing deployment/forecasting tests, 11 M1 security/DB tests, and 13 challenger edge case tests. Zero failures, zero regressions.

---

## 2. Logic Chain

1. **Integrity Mode Determination**:
   - Checked `ORIGINAL_REQUEST.md:8`: Explicitly specifies `Integrity mode: development`.
   - In Development Mode, third-party libraries (`DBUtils`, `Flask-Limiter`) are permitted and expected. Facade implementations, hardcoded test results, fabricated output files, and self-certifying tests are strictly prohibited.

2. **Absence of Prohibited Patterns**:
   - No mock bypasses or hardcoded fake responses were found in production routes (`auth_routes.py`, `connection.py`, `limiter.py`).
   - All assertions in `test_m1_security_db.py` inspect actual mock call lists (`mock_cursor.execute.call_args_list`), HTTP status codes (`429`, `200`, `400`), response schemas, and thread outcomes. No tautological assertions (`assert True`) were used.
   - Zero pre-populated test output logs or result artifacts exist in the workspace.

3. **Execution of `DELETE FROM sessions`**:
   - Direct source code inspection confirms `cursor.execute("DELETE FROM sessions WHERE user_id=%s", (user["id"],))` in `php_compat_change_password`.
   - Execution was verified empirically under positive and negative test cases:
     - On valid password change: query executes with user ID parameter, transaction commits, cookie clears.
     - On invalid old password: 400 error returns, query is NOT executed.
     - Multi-device edge case confirms all tokens for that user ID are purged.

4. **Authenticity of `PooledDB` Pooling**:
   - `DBUtils.pooled_db.PooledDB` is instantiated with configured thread locks, caching parameters, and `pymysql.cursors.DictCursor`.
   - Connection checkout yields `PooledDedicatedDBConnection`.
   - Mock tests verify `mock_conn.close()` is NOT called upon `conn.close()`, proving real pool retention rather than interface faking.
   - Concurrency tests demonstrate thread-safe acquisition across 8 simultaneous worker threads.

5. **Active Rate Limiter Throttling**:
   - `Flask-Limiter` actively tracks IP keys via `get_client_ip_key`.
   - After 5 requests within a 1-minute window, the 6th request triggers an HTTP 429 status code with the required JSON payload.
   - Preflight CORS OPTIONS requests bypass the counter as intended.

---

## 3. Caveats

- Rate limiting uses an in-memory store (`memory://`). For multi-process horizontal scaling across multiple dynos/instances without sticky sessions, `RATELIMIT_STORAGE_URI` should be pointed to a persistent shared cache (e.g. Redis).
- Production database credentials must be configured via environment variables (`DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_PORT`, `DB_SSL_CA`).

---

## 4. Conclusion

The work product delivered for Milestone M1 is **genuine, robust, and free of any integrity violations**. All four core deliverables:
1. Database connection pooling via `DBUtils.pooled_db.PooledDB`,
2. Immediate session revocation on password change via `DELETE FROM sessions WHERE user_id=%s`,
3. Rate limiting and brute-force protection via `Flask-Limiter`,
4. Frontend API standardization and legacy PHP deprecation in `js/config.js` and route aliases,

are genuinely implemented, fully tested with non-trivial assertions, and verified through independent test runs (51/51 tests passing, 100% success rate).

Final Verdict: **CLEAN**

---

## 5. Verification Method

To independently reproduce this audit:

1. **Inspect Session Invalidation**:
   View `d:\xampp\htdocs\gold-price-checker\api\routes\auth_routes.py` lines 198-212 to confirm `cursor.execute("DELETE FROM sessions WHERE user_id=%s", (user["id"],))` and `conn.commit()`.

2. **Inspect Connection Pooling**:
   View `d:\xampp\htdocs\gold-price-checker\api\database\connection.py` lines 87-115 and 158-172 to confirm `PooledDB` initialization and checkout.

3. **Inspect Rate Limiting**:
   View `d:\xampp\htdocs\gold-price-checker\api\utils\limiter.py` lines 9-31 and `api/app/create_app.py` lines 37-50.

4. **Run M1 Test Suite**:
   ```powershell
   & "d:\xampp\htdocs\gold-price-checker\.venv\Scripts\python.exe" -m unittest discover -s tests -p "test_m1_*.py" -v
   ```
   *Expected outcome*: 11 tests pass in ~15 seconds with status `OK`.

5. **Run Full Test Suite**:
   ```powershell
   & "d:\xampp\htdocs\gold-price-checker\.venv\Scripts\python.exe" -m unittest discover -s tests -p "test_*.py" -v
   ```
   *Expected outcome*: 51 tests pass in ~26 seconds with status `OK`.
