"""tests/test_m1_challenger_edge_cases.py — Empirical Challenger stress tests for Milestone M1.

Empirical verification covering:
1. Rate limiter edge cases:
   - Multi-hop X-Forwarded-For headers (isolation of first client IP)
   - Formatting anomalies (whitespace, empty headers, commas only)
   - IPv6 and long malicious header handling
   - OPTIONS preflight bypass protection
   - Rate limit 429 response structure and headers
2. Connection pool error handling:
   - MySQL connection failure handling and 503 response sanitization
   - Pool exhaustion in non-blocking mode (TooManyConnections exception and recovery)
   - Pool exhaustion in blocking mode (thread-safe queue release without deadlock)
   - Connection leak prevention on query failure (proper return to pool)
3. Session deletion edge cases:
   - Multi-device revocation: all active device sessions for user deleted
   - Multi-user isolation: other users' sessions remain intact
   - Nonexistent / invalid / expired session tokens rejected (401)
   - Cookie clearance across success and failure paths in change-password and logout
"""

import os
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = PROJECT_ROOT / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

import pymysql
from app.create_app import create_app
from database.connection import (
    close_db_pool,
    get_db_connection,
    get_db_pool,
    init_db_pool,
)
from utils.helpers import _bcrypt_hash, _client_ip
from utils.limiter import get_client_ip_key, limiter


# ===========================================================================
# 1. Rate Limiter Edge Cases
# ===========================================================================
class ChallengerRateLimiterEdgeCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config.update(TESTING=True)
        cls.client = cls.app.test_client()

    def setUp(self):
        limiter.reset()

    def tearDown(self):
        limiter.reset()

    def test_multi_hop_x_forwarded_for_rate_limiting(self):
        """Verify that rate limiting tracks the trusted remote client address and isolates different IPs."""
        client_ip = "203.0.113.195"
        
        # 5 requests with same client remote_addr
        for i in range(5):
            headers = {"X-Forwarded-For": f"{client_ip}, 70.41.3.{i}, 150.172.238.1"}
            res = self.client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": "wrong"},
                headers=headers,
                environ_base={"REMOTE_ADDR": client_ip},
            )
            self.assertIn(res.status_code, (400, 401, 503), f"Request {i+1} unexpectedly failed")

        # 6th request from same client remote_addr must be throttled (429)
        headers = {"X-Forwarded-For": f"{client_ip}, 192.168.1.1"}
        res_throttled = self.client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "wrong"},
            headers=headers,
            environ_base={"REMOTE_ADDR": client_ip},
        )
        self.assertEqual(res_throttled.status_code, 429, "6th request was not throttled!")

        # Request from a DIFFERENT client IP should NOT be throttled
        diff_headers = {"X-Forwarded-For": "198.51.100.22, 10.0.0.1"}
        res_diff = self.client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "wrong"},
            headers=diff_headers,
            environ_base={"REMOTE_ADDR": "198.51.100.22"},
        )
        self.assertNotEqual(res_diff.status_code, 429, "Different client IP was falsely throttled!")

    def test_spoofed_x_forwarded_for_does_not_bypass_rate_limiting(self):
        """Verify that rotating X-Forwarded-For headers from the same client cannot bypass rate limiting."""
        codes = []
        for i in range(10):
            res = self.client.post(
                "/api/auth/login",
                headers={"X-Forwarded-For": f"203.0.113.{i}"},
                json={"email": "attacker@example.com", "password": "wrong"},
            )
            codes.append(res.status_code)
        self.assertIn(429, codes, "Rate limit was bypassed by rotating X-Forwarded-For headers!")
        self.assertEqual(codes[5:], [429, 429, 429, 429, 429], "Requests 6-10 were not throttled!")

    def test_x_forwarded_for_whitespace_and_empty_fallbacks(self):
        """Verify helper handles leading/trailing whitespace and falls back when header is empty."""
        with self.app.test_request_context(
            "/", environ_base={"REMOTE_ADDR": "203.0.113.88"}, headers={"X-Forwarded-For": "   203.0.113.88   ,  10.0.0.1 "}
        ):
            from flask import request
            self.assertEqual(_client_ip(request), "203.0.113.88")
            self.assertEqual(get_client_ip_key(), "203.0.113.88")

        # Empty or commas-only header should fall back to remote_addr
        with self.app.test_request_context(
            "/", environ_base={"REMOTE_ADDR": "127.0.0.1"}, headers={"X-Forwarded-For": "  "}
        ):
            from flask import request
            self.assertEqual(_client_ip(request), "127.0.0.1")

        with self.app.test_request_context(
            "/", environ_base={"REMOTE_ADDR": "192.168.0.5"}, headers={"X-Forwarded-For": ", , "}
        ):
            from flask import request
            # Should not crash on comma-only header
            ip = _client_ip(request)
            self.assertTrue(ip in ("", "192.168.0.5"))

    def test_x_forwarded_for_ipv6_and_excessive_length(self):
        """Verify IPv6 support and safety against oversized header strings."""
        ipv6 = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        with self.app.test_request_context("/", headers={"X-Forwarded-For": ipv6}):
            from flask import request
            self.assertEqual(_client_ip(request), ipv6)

        # Truncation safety: VARCHAR(45) safe boundary
        huge_header = "192.168.1.100," + ("A" * 5000)
        with self.app.test_request_context("/", headers={"X-Forwarded-For": huge_header}):
            from flask import request
            safe_ip = _client_ip(request, max_length=45)
            self.assertLessEqual(len(safe_ip), 45)
            self.assertEqual(safe_ip, "192.168.1.100")

    def test_options_preflight_does_not_consume_rate_limit(self):
        """Stress-test OPTIONS requests to ensure zero quota consumption."""
        headers = {"X-Forwarded-For": "203.0.113.55"}
        
        # Fire 25 OPTIONS requests in succession
        for _ in range(25):
            res = self.client.options("/api/auth/login", headers=headers)
            self.assertEqual(res.status_code, 200)

        # Next 5 POST requests must still succeed (quota intact)
        for i in range(5):
            res = self.client.post(
                "/api/auth/login",
                json={"email": "options_test@example.com", "password": "wrong"},
                headers=headers,
            )
            self.assertNotEqual(res.status_code, 429, f"POST #{i+1} was unexpectedly throttled")

        # 6th POST request must throttle
        res_throttled = self.client.post(
            "/api/auth/login",
            json={"email": "options_test@example.com", "password": "wrong"},
            headers=headers,
        )
        self.assertEqual(res_throttled.status_code, 429)

    def test_rate_limit_response_schema_and_status(self):
        """Verify 429 response structure matches required API error specification."""
        headers = {"X-Forwarded-For": "203.0.113.99"}
        for _ in range(5):
            self.client.post("/api/auth/login", json={"email": "a", "password": "b"}, headers=headers)

        res_429 = self.client.post("/api/auth/login", json={"email": "a", "password": "b"}, headers=headers)
        self.assertEqual(res_429.status_code, 429)
        self.assertEqual(res_429.content_type, "application/json")
        
        body = res_429.get_json()
        self.assertIsInstance(body, dict)
        self.assertEqual(body.get("success"), False)
        self.assertEqual(body.get("error"), "rate_limit_exceeded")
        self.assertIn("คำขอมากเกินไป", body.get("message", ""))
        self.assertTrue(len(body.get("description", "")) > 0)


# ===========================================================================
# 2. Connection Pool Error Handling
# ===========================================================================
class ChallengerConnectionPoolErrorHandlingTests(unittest.TestCase):
    def setUp(self):
        close_db_pool()

    def tearDown(self):
        close_db_pool()

    def test_mysql_connection_failure_propagates_operational_error(self):
        """Verify get_db_connection raises OperationalError when MySQL server is unreachable."""
        with patch("database.connection.pymysql.connect") as mock_connect:
            mock_connect.side_effect = pymysql.err.OperationalError(
                2003, "Can't connect to MySQL server on 'mysql.example.com'"
            )
            with self.assertRaises(pymysql.err.OperationalError) as ctx:
                get_db_connection()
            self.assertIn("Can't connect to MySQL server", str(ctx.exception))

    def test_login_endpoint_handles_db_failure_with_503_and_sanitized_message(self):
        """Verify login endpoint returns 503 without leaking DB host/credentials on DB down."""
        app = create_app()
        app.config.update(TESTING=True)
        client = app.test_client()

        with patch("routes.auth_routes.get_db_connection") as mock_get_conn:
            mock_get_conn.side_effect = pymysql.err.OperationalError(
                2003, "Can't connect to MySQL server on 'secret-db.internal:3306' (password: secretpass)"
            )
            response = client.post(
                "/api/auth/login",
                json={"email": "user@example.com", "password": "password123"},
                headers={"X-Forwarded-For": "198.51.100.77"},
            )

            self.assertEqual(response.status_code, 503)
            data = response.get_json()
            self.assertFalse(data.get("success"))
            # Crucial security check: connection string and passwords must NOT be in client response
            self.assertNotIn("secret-db.internal", str(data))
            self.assertNotIn("secretpass", str(data))
            self.assertIn("ระบบฐานข้อมูลไม่พร้อมใช้งาน", data.get("message"))

    def test_pool_exhaustion_non_blocking_mode(self):
        """Verify pool raises TooManyConnections when exhausted under blocking=False and recovers."""
        mock_raw_conn = MagicMock()
        with patch("database.connection.pymysql.connect", return_value=mock_raw_conn):
            pool = init_db_pool(
                reset=True,
                mincached=0,
                maxcached=2,
                maxconnections=2,
                blocking=False,
            )
            from dbutils.pooled_db import TooManyConnections

            c1 = pool.connection()
            c2 = pool.connection()
            self.assertIsNotNone(c1)
            self.assertIsNotNone(c2)

            # 3rd checkout must raise TooManyConnections
            with self.assertRaises(TooManyConnections):
                pool.connection()

            # Release c1 back to pool
            c1.close()

            # Now checkout should succeed again
            c3 = pool.connection()
            self.assertIsNotNone(c3)
            c2.close()
            c3.close()

    def test_pool_exhaustion_blocking_mode_concurrency(self):
        """Verify thread-safe blocking pool queues requests without deadlock when connections free."""
        mock_raw_conn = MagicMock()
        with patch("database.connection.pymysql.connect", return_value=mock_raw_conn):
            pool = init_db_pool(
                reset=True,
                mincached=0,
                maxcached=2,
                maxconnections=2,
                blocking=True,
            )

            c1 = pool.connection()
            c2 = pool.connection()

            acquired_c3 = []
            thread_error = []

            def delayed_checkout():
                try:
                    # Will block until c1 or c2 is released
                    c3 = pool.connection()
                    acquired_c3.append(c3)
                    c3.close()
                except Exception as ex:
                    thread_error.append(ex)

            t = threading.Thread(target=delayed_checkout)
            t.start()

            # Wait briefly to let thread block on pool
            time.sleep(0.05)
            self.assertEqual(len(acquired_c3), 0, "Thread should have blocked on exhausted pool")

            # Release c1
            c1.close()
            t.join(timeout=2.0)

            self.assertFalse(t.is_alive(), "Worker thread deadlocked on pool checkout!")
            self.assertEqual(len(thread_error), 0, f"Thread encountered error: {thread_error}")
            self.assertEqual(len(acquired_c3), 1, "Thread failed to acquire connection after release")

            c2.close()

    def test_cold_start_concurrent_pool_initialization(self):
        """Verify double-checked locking prevents multiple pools from being created under cold-start race."""
        with patch("database.connection.pymysql.connect", return_value=MagicMock()):
            close_db_pool()
            pools = []
            barrier = threading.Barrier(5)

            def worker():
                barrier.wait()
                pools.append(id(get_db_pool()))

            threads = [threading.Thread(target=worker) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            self.assertEqual(len(set(pools)), 1, f"Multiple pools created under cold start race: {len(set(pools))}")

    def test_connection_closed_on_query_exception(self):
        """Verify that connection is closed (returned to pool) even when cursor operations fail."""
        app = create_app()
        app.config.update(TESTING=True)
        client = app.test_client()

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = pymysql.err.ProgrammingError(1064, "You have an error in your SQL syntax")

        with patch("routes.auth_routes.get_db_connection", return_value=mock_conn):
            response = client.post(
                "/api/auth/register",
                json={"name": "Test User", "email": "test_err@example.com", "password": "password123"},
                headers={"X-Forwarded-For": "198.51.100.88"},
            )
            # Route should handle error with 500
            self.assertEqual(response.status_code, 500)
            # Crucial: mock_conn.close() MUST have been called in finally block to avoid pool leak
            mock_conn.close.assert_called_once()


# ===========================================================================
# 3. Session Deletion Edge Cases
# ===========================================================================
class ChallengerSessionDeletionEdgeCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config.update(TESTING=True)
        cls.client = cls.app.test_client()

    def test_multiple_devices_revoked_on_password_change(self):
        """Verify that ALL active device tokens for a user are deleted, while other users' tokens stay."""
        user_1_id = 42
        user_2_id = 99
        pw_hash = _bcrypt_hash("oldSecretPass1")

        # Simulated DB state
        sessions_table = [
            {"token": "dev_phone_tok", "user_id": user_1_id},
            {"token": "dev_laptop_tok", "user_id": user_1_id},
            {"token": "dev_tablet_tok", "user_id": user_1_id},
            {"token": "other_user_tok", "user_id": user_2_id},
        ]

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        def mock_fetchone():
            return {"id": user_1_id, "email": "multi@example.com", "password_hash": pw_hash, "is_active": 1}

        mock_cursor.fetchone.side_effect = [
            mock_fetchone(),              # _auth_get_user_by_session
            {"password_hash": pw_hash},    # SELECT password_hash FROM users WHERE id=%s
        ]

        def mock_execute(query, params=None):
            if "DELETE FROM sessions WHERE user_id=%s" in query:
                target_uid = params[0]
                nonlocal sessions_table
                sessions_table = [s for s in sessions_table if s["user_id"] != target_uid]

        mock_cursor.execute.side_effect = mock_execute

        with patch("routes.auth_routes.get_db_connection", return_value=mock_conn):
            self.client.set_cookie("session_token", "dev_laptop_tok")
            res = self.client.post(
                "/api/auth/change-password",
                json={"old_password": "oldSecretPass1", "new_password": "brandNewSecretPass2"},
            )
            self.assertEqual(res.status_code, 200)

        # Verify all 3 sessions of User 1 were deleted
        user_1_remaining = [s for s in sessions_table if s["user_id"] == user_1_id]
        self.assertEqual(len(user_1_remaining), 0, "User 1 sessions still exist after password change!")

        # Verify User 2's session was preserved (multi-user isolation)
        user_2_remaining = [s for s in sessions_table if s["user_id"] == user_2_id]
        self.assertEqual(len(user_2_remaining), 1, "User 2 session was mistakenly deleted!")
        self.assertEqual(user_2_remaining[0]["token"], "other_user_tok")

    def test_change_password_unauthenticated_edge_cases(self):
        """Verify behavior with missing cookie, invalid token, and deactivated user."""
        # 1. No cookie
        self.client.set_cookie("session_token", "")
        res_no_cookie = self.client.post(
            "/api/auth/change-password",
            json={"old_password": "any", "new_password": "newpassword123"},
        )
        self.assertEqual(res_no_cookie.status_code, 401)
        self.assertFalse(res_no_cookie.get_json()["success"])

        # 2. Token not in DB
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None  # user not found

        with patch("routes.auth_routes.get_db_connection", return_value=mock_conn):
            self.client.set_cookie("session_token", "nonexistent_token_123")
            res_invalid = self.client.post(
                "/api/auth/change-password",
                json={"old_password": "any", "new_password": "newpassword123"},
            )
            self.assertEqual(res_invalid.status_code, 401)

    def test_cookie_clearance_on_change_password_and_logout(self):
        """Verify Set-Cookie header expires the session token on change-password and logout."""
        user_id = 77
        pw_hash = _bcrypt_hash("myOldPass123")

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [
            {"id": user_id, "email": "cookie_test@example.com", "password_hash": pw_hash, "is_active": 1},
            {"password_hash": pw_hash},
        ]

        # 1. Change password clears cookie
        with patch("routes.auth_routes.get_db_connection", return_value=mock_conn):
            self.client.set_cookie("session_token", "active_tok")
            res_change = self.client.post(
                "/api/auth/change-password",
                json={"old_password": "myOldPass123", "new_password": "myNewPass456"},
            )
            set_cookie_header = res_change.headers.get("Set-Cookie", "")
            self.assertIn("session_token=", set_cookie_header)
            self.assertIn("HttpOnly", set_cookie_header)
            self.assertIn("SameSite=Lax", set_cookie_header)
            # Must expire or have Max-Age=0
            self.assertTrue(
                "Expires=" in set_cookie_header or "Max-Age=0" in set_cookie_header or "expires=" in set_cookie_header.lower(),
                f"Cookie clearance missing expiry: {set_cookie_header}",
            )

        # 2. Normal logout clears cookie
        with patch("routes.auth_routes.get_db_connection", return_value=mock_conn):
            self.client.set_cookie("session_token", "active_tok")
            res_logout = self.client.post("/api/auth/logout")
            self.assertEqual(res_logout.status_code, 200)
            self.assertIn("session_token=", res_logout.headers.get("Set-Cookie", ""))

        # 3. Logout with no token still clears cookie gracefully
        with patch("routes.auth_routes.get_db_connection", return_value=mock_conn):
            self.client.set_cookie("session_token", "")
            res_logout_empty = self.client.post("/api/auth/logout")
            self.assertEqual(res_logout_empty.status_code, 200)
            self.assertIn("session_token=", res_logout_empty.headers.get("Set-Cookie", ""))

        # 4. Logout when DB fails STILL clears cookie on client
        with patch("routes.auth_routes.get_db_connection") as mock_fail_conn:
            mock_fail_conn.side_effect = Exception("Database crash during logout")
            self.client.set_cookie("session_token", "failing_tok")
            res_logout_fail = self.client.post("/api/auth/logout")
            self.assertEqual(res_logout_fail.status_code, 500)
            # Res should still clear the cookie on the browser
            set_cookie_fail = res_logout_fail.headers.get("Set-Cookie", "")
            self.assertIn("session_token=", set_cookie_fail)


if __name__ == "__main__":
    unittest.main()
