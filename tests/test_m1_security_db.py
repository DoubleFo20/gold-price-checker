"""tests/test_m1_security_db.py — Test suite for M1 Backend Security & DB Pooling.

Covers:
1. Thread-safe DB connection pooling via DBUtils.pooled_db.PooledDB wrapping PyMySQL DictCursor.
2. Active session revocation upon password change (DELETE FROM sessions WHERE user_id=%s).
3. Rate limiting on authentication routes (Flask-Limiter) and 429 JSON response.
4. Route aliases and backwards compatibility for deprecated PHP endpoints.
"""

import os
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = PROJECT_ROOT / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.create_app import create_app
from database.connection import (
    PooledDB,
    close_db_pool,
    get_db_connection,
    get_db_pool,
    init_db_pool,
)
from utils.helpers import _bcrypt_hash
from utils.limiter import limiter


class DatabaseConnectionPoolingTests(unittest.TestCase):
    def setUp(self):
        close_db_pool()

    def tearDown(self):
        close_db_pool()

    def test_dbutils_pooled_db_instance(self):
        """Verify that get_db_pool returns a valid PooledDB instance wrapping PyMySQL."""
        mock_conn = MagicMock()
        with patch("database.connection.pymysql.connect", return_value=mock_conn):
            pool = get_db_pool()
            self.assertIsNotNone(pool)
            self.assertIsInstance(pool, PooledDB)

    def test_pooled_connection_checkout_and_close(self):
        """Verify that get_db_connection checks out from the pool and close() returns to pool."""
        mock_conn = MagicMock()
        with patch("database.connection.pymysql.connect", return_value=mock_conn):
            conn = get_db_connection()
            self.assertIsNotNone(conn)
            # The connection should be a DBUtils PooledDedicatedDBConnection wrapper
            self.assertTrue(hasattr(conn, "cursor"))
            self.assertTrue(hasattr(conn, "close"))
            
            # Close connection (returns to pool)
            conn.close()
            # Under mock, the underlying mock_conn.close should NOT be called directly
            # because PooledDB returns the connection to the idle pool
            mock_conn.close.assert_not_called()

    def test_thread_safe_pool_concurrency(self):
        """Verify that multiple concurrent threads can obtain connections without deadlock."""
        mock_conn = MagicMock()
        errors = []

        def worker():
            try:
                with patch("database.connection.pymysql.connect", return_value=mock_conn):
                    c = get_db_connection()
                    cur = c.cursor()
                    cur.close()
                    c.close()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Thread errors encountered: {errors}")

    def test_close_and_reinit_db_pool(self):
        """Verify that close_db_pool resets the pool and get_db_pool reinitializes it."""
        mock_conn = MagicMock()
        with patch("database.connection.pymysql.connect", return_value=mock_conn):
            p1 = get_db_pool()
            self.assertIsNotNone(p1)
            close_db_pool()
            # Calling get_db_pool again should create a fresh pool
            p2 = get_db_pool()
            self.assertIsNotNone(p2)


class ActiveSessionRevocationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config.update(TESTING=True)
        cls.client = cls.app.test_client()

    def test_password_change_deletes_all_user_sessions(self):
        """Verify that /api/auth/change-password executes DELETE FROM sessions WHERE user_id=%s."""
        old_pw = "validOldPassword123"
        hashed = _bcrypt_hash(old_pw)
        user_id = 101

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        user_row = {
            "id": user_id,
            "email": "revoke_test@example.com",
            "password_hash": hashed,
            "role": "user",
            "is_active": 1,
        }

        mock_cursor.fetchone.side_effect = [
            user_row,                   # _auth_get_user_by_session
            {"password_hash": hashed},   # SELECT password_hash FROM users WHERE id=%s
        ]

        with patch("routes.auth_routes.get_db_connection", return_value=mock_conn):
            self.client.set_cookie("session_token", "test_active_token_abc")
            response = self.client.post(
                "/api/auth/change-password",
                json={"old_password": old_pw, "new_password": "brandNewPassword456"},
            )

            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data.get("success"))

            # Inspect all SQL statements executed on the cursor
            executed_queries = [call[0][0] for call in mock_cursor.execute.call_args_list]
            executed_params = [call[0][1] for call in mock_cursor.execute.call_args_list if len(call[0]) > 1]

            # Verify DELETE FROM sessions WHERE user_id=%s was executed with user_id
            session_delete_found = False
            for q, p in zip(executed_queries, executed_params):
                if "DELETE FROM sessions WHERE user_id=%s" in q:
                    session_delete_found = True
                    self.assertEqual(p, (user_id,))
            self.assertTrue(session_delete_found, "DELETE FROM sessions WHERE user_id=%s was not executed!")

            # Verify commit was called
            mock_conn.commit.assert_called_once()

    def test_php_compat_change_password_alias_deletes_sessions(self):
        """Verify that legacy /api/api/auth/change_password.php also invalidates active sessions."""
        old_pw = "legacyOldPassword123"
        hashed = _bcrypt_hash(old_pw)
        user_id = 202

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        user_row = {
            "id": user_id,
            "email": "legacy_revoke@example.com",
            "password_hash": hashed,
            "role": "user",
            "is_active": 1,
        }

        mock_cursor.fetchone.side_effect = [
            user_row,
            {"password_hash": hashed},
        ]

        with patch("routes.auth_routes.get_db_connection", return_value=mock_conn):
            self.client.set_cookie("session_token", "legacy_token_xyz")
            response = self.client.post(
                "/api/api/auth/change_password.php",
                json={"old_password": old_pw, "new_password": "brandNewPassword789"},
            )

            self.assertEqual(response.status_code, 200)
            executed_queries = [call[0][0] for call in mock_cursor.execute.call_args_list]
            self.assertTrue(
                any("DELETE FROM sessions WHERE user_id=%s" in q for q in executed_queries),
                "DELETE FROM sessions was not called via PHP-compat route!",
            )

    def test_failed_password_change_does_not_delete_sessions(self):
        """Verify that an invalid old password does not delete sessions."""
        user_id = 303
        hashed = _bcrypt_hash("correctPassword123")

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        user_row = {
            "id": user_id,
            "email": "wrong_pw@example.com",
            "password_hash": hashed,
            "role": "user",
            "is_active": 1,
        }

        mock_cursor.fetchone.side_effect = [
            user_row,
            {"password_hash": hashed},
        ]

        with patch("routes.auth_routes.get_db_connection", return_value=mock_conn):
            self.client.set_cookie("session_token", "valid_token")
            response = self.client.post(
                "/api/auth/change-password",
                json={"old_password": "WRONG_PASSWORD", "new_password": "newPassword123"},
            )

            self.assertEqual(response.status_code, 400)
            executed_queries = [call[0][0] for call in mock_cursor.execute.call_args_list]
            self.assertFalse(
                any("DELETE FROM sessions" in q for q in executed_queries),
                "Sessions were deleted despite invalid password!",
            )


class RateLimitingThrottlingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config.update(TESTING=True)
        cls.client = cls.app.test_client()

    def setUp(self):
        limiter.reset()

    def tearDown(self):
        limiter.reset()

    def test_login_rate_limiting_throttles_after_limit(self):
        """Verify that login endpoint throttles requests beyond 5 per minute with 429."""
        status_codes = []
        for _ in range(6):
            res = self.client.post(
                "/api/auth/login",
                json={"email": "throttle_test@example.com", "password": "wrong"},
            )
            status_codes.append(res.status_code)

        # First 5 requests should pass through to auth handler (401 or 400 or 503)
        for code in status_codes[:5]:
            self.assertIn(code, (400, 401, 503))

        # 6th request must be throttled with HTTP 429
        self.assertEqual(status_codes[5], 429)

        # Check JSON response structure
        res_429 = self.client.post(
            "/api/auth/login",
            json={"email": "throttle_test@example.com", "password": "wrong"},
        )
        self.assertEqual(res_429.status_code, 429)
        json_data = res_429.get_json()
        self.assertFalse(json_data.get("success"))
        self.assertEqual(json_data.get("error"), "rate_limit_exceeded")

    def test_php_compat_login_shares_rate_limit(self):
        """Verify that legacy /api/api/auth/login.php is also throttled by the same limit."""
        status_codes = []
        for _ in range(6):
            res = self.client.post(
                "/api/api/auth/login.php",
                json={"email": "throttle_php@example.com", "password": "wrong"},
            )
            status_codes.append(res.status_code)

        self.assertEqual(status_codes[5], 429)

    def test_options_preflight_is_exempt_from_rate_limit(self):
        """Verify that CORS preflight OPTIONS requests do not consume rate limit tokens."""
        for _ in range(10):
            res = self.client.options("/api/auth/login")
            self.assertEqual(res.status_code, 200)

        # After 10 OPTIONS requests, a regular POST should still have its full quota
        res_post = self.client.post(
            "/api/auth/login",
            json={"email": "options_exempt@example.com", "password": "wrong"},
        )
        self.assertNotEqual(res_post.status_code, 429)


class RouteAliasesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_all_auth_and_user_route_aliases_exist(self):
        """Verify all canonical /api/* and backwards-compatible /api/api/*.php routes exist in URL map."""
        endpoints = [rule.rule for rule in self.app.url_map.iter_rules()]

        expected_rules = [
            "/api/auth/login",
            "/api/auth/login.php",
            "/api/api/auth/login.php",
            "/api/auth/register",
            "/api/auth/register.php",
            "/api/api/auth/register.php",
            "/api/auth/check-session",
            "/api/auth/check_session",
            "/api/api/auth/check_session.php",
            "/api/auth/change-password",
            "/api/auth/change_password",
            "/api/api/auth/change_password.php",
            "/api/auth/logout",
            "/api/auth/logout.php",
            "/api/api/auth/logout.php",
            "/api/alerts/create",
            "/api/alerts/create.php",
            "/api/api/alerts/create.php",
            "/api/alerts",
            "/api/alerts/list.php",
            "/api/api/alerts/list.php",
            "/api/profile/update-push",
            "/api/profile/update_push.php",
            "/api/api/profile/update_push.php",
            "/api/user/save-forecast",
            "/api/user/save_forecast.php",
            "/api/api/user/save_forecast.php",
        ]

        for expected in expected_rules:
            self.assertIn(expected, endpoints, f"Expected route {expected} not found in url_map")


if __name__ == "__main__":
    unittest.main()
