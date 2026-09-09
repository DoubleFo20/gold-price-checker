## 2026-09-09T15:46:18Z
You are worker_m1 (Agent C - Backend Security & Database Architecture).
Your working directory is: d:\xampp\htdocs\gold-price-checker\.agents\worker_m1
Project workspace root: d:\xampp\htdocs\gold-price-checker
Mandatory reading: You MUST read d:\xampp\htdocs\gold-price-checker\.agents\ORIGINAL_REQUEST.md, d:\xampp\htdocs\gold-price-checker\.agents\PROJECT.md, and d:\xampp\htdocs\gold-price-checker\.agents\explorer_survey_1\handoff.md and d:\xampp\htdocs\gold-price-checker\.agents\explorer_survey_3\handoff.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your objectives:
1. Database Connection Pooling:
   - Install `DBUtils` in `.venv` (d:\xampp\htdocs\gold-price-checker\.venv\Scripts\pip.exe install DBUtils) and add DBUtils to requirements.txt.
   - Refactor `api/database/connection.py` to implement thread-safe connection pooling with `DBUtils.pooled_db.PooledDB` wrapping PyMySQL DictCursor.
2. Active Session Revocation on Password Change:
   - In `api/routes/auth_routes.py`, update password change logic (`php_compat_change_password` and `/api/auth/change-password`): immediately execute `DELETE FROM sessions WHERE user_id=%s` so all prior active session tokens are revoked upon password change.
3. Rate Limiting via Flask-Limiter:
   - Install `Flask-Limiter` in `.venv` (d:\xampp\htdocs\gold-price-checker\.venv\Scripts\pip.exe install Flask-Limiter) and add flask-limiter to requirements.txt.
   - Configure Limiter in `api/app/create_app.py` or middleware (using remote address key). Apply rate limiting to auth routes (`/api/api/auth/login.php`, `/api/api/auth/register.php`, `/api/auth/login`, `/api/auth/register`, etc. e.g. 5 per minute).
4. Deprecate Legacy PHP & Standardize Frontend API Calls:
   - Update `js/config.js` to standardize all API calls to relative `/api/*` endpoints handled directly by Flask.
   - Ensure Flask provides routes and backwards-compatible aliases for all frontend endpoints.
5. Verification:
   - Run existing unit tests (`.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"`).
   - Write new unit tests in `tests/test_m1_security_db.py` verifying connection pooling, session revocation on password change, and rate limiting throttling. Run all tests and verify 100% pass.
   - Write your complete handoff report to `d:\xampp\htdocs\gold-price-checker\.agents\worker_m1\handoff.md` with: Observation, Logic Chain, Caveats, Conclusion, Verification Method.
   - Send a completion message back to parent.
