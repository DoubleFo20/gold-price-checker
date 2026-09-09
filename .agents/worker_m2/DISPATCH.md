## 2026-09-09T16:18:03Z

You are worker_m2 (Agent D - Notifications & Auth Flow Champion).
Your working directory is: d:\xampp\htdocs\gold-price-checker\.agents\worker_m2
Project workspace root: d:\xampp\htdocs\gold-price-checker
Mandatory reading: Read d:\xampp\htdocs\gold-price-checker\.agents\ORIGINAL_REQUEST.md, d:\xampp\htdocs\gold-price-checker\.agents\PROJECT.md, d:\xampp\htdocs\gold-price-checker\.agents\explorer_survey_1\handoff.md, and d:\xampp\htdocs\gold-price-checker\.agents\explorer_survey_3\handoff.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Objectives:
Execute Milestone M2 (Notifications & Auth Flow):
1. Email Verification & Password Reset Flows in Flask:
   - In `api/routes/auth_routes.py`:
     - Implement `/api/auth/forgot-password` (alias `/api/api/auth/forgot.php`): generates a secure random token, inserts into `password_resets` (`user_id, token, expires_at`), dispatches reset email.
     - Implement `/api/auth/reset-password` (alias `/api/api/auth/reset.php`): verifies token from `password_resets`, updates `users.password_hash`, immediately deletes all active user sessions from `sessions`, deletes used token.
     - Implement `/api/auth/verify-email` (alias `/api/api/auth/verify.php`): validates token from `email_verifications`, updates `users.is_verified=1`, deletes token.
     - Implement `/api/auth/resend-verify` (alias `/api/api/auth/resend_verify.php`): generates token in `email_verifications`, dispatches verification email.
2. Responsive HTML Email Delivery & Delivery Logging:
   - In `api/services/email_service.py`:
     - Implement `send_verification_email(email, name, token)` and `send_password_reset_email(email, name, token)`.
     - Implement clean, responsive HTML email templates for alerts, verification, reset, and forecast summaries.
     - Implement delivery tracking in `email_logs` table (`recipient, subject, status, error_message, sent_at`): every outbound email attempt (success or failure) must record an entry in `email_logs`.
3. Service Worker Web Push Hardening:
   - In `sw.js`:
     - Add try-catch error handling around `event.data.json()` with fallback to text or default payload.
     - In `notificationclick`, use `clients.matchAll({ type: "window", includeUncontrolled: true })` to find and focus an existing open tab if one exists, otherwise open a new window.
4. Scheduled Daily Morning Price Notification:
   - In `api/services/scheduler.py`:
     - Add `job_morning_price_summary()`: fetches latest gold prices and dispatches daily summary notifications to opted-in users / channels.
5. Verification:
   - Create unit tests in `tests/test_m2_notifications_auth.py` verifying token generation, email logging, session revocation during reset, and notification dispatch.
   - Run tests: `& "d:\xampp\htdocs\gold-price-checker\.venv\Scripts\python.exe" -m unittest discover -s tests -p "test_*.py" -v` and `& "d:\xampp\htdocs\gold-price-checker\.venv\Scripts\pytest.exe" tests/ -q`.
   - Ensure 100% pass rate.
   - Write your handoff report to `d:\xampp\htdocs\gold-price-checker\.agents\worker_m2\handoff.md` and send a completion message back.
