#!/usr/bin/env python3
"""empirical_stress_test.py — Empirical challenge and stress-test suite for Milestone M1.

Evaluates:
1. Connection pool concurrency: 10 concurrent worker threads checking out and checking in
   connections simultaneously to verify thread safety and absence of deadlocks.
2. Session revocation: Create active sessions for a user, call password change, and confirm
   with certainty that previous sessions are invalid and rejected across all endpoints.
3. Rate limiting: Send 6 consecutive rapid requests to /api/auth/login to confirm the 6th
   request is blocked with HTTP 429 and returns structured JSON error.

Executed by: challenger_m1_1
"""

import copy
import datetime
import json
import os
import sys
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure API root is importable
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
API_ROOT = PROJECT_ROOT / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

# Project imports
from app.create_app import create_app
from database.connection import (
    PooledDB,
    close_db_pool,
    get_db_connection,
    get_db_pool,
    init_db_pool,
)
from utils.helpers import _bcrypt_hash, _bcrypt_verify
from utils.limiter import limiter


# ============================================================================
# 1. EMPIRICAL CHALLENGE: CONNECTION POOL CONCURRENCY & DEADLOCK RESISTANCE
# ============================================================================
class SimulatedDBConnection:
    """Thread-aware simulated database connection to measure concurrency & contention."""
    _counter_lock = threading.Lock()
    _active_connections = 0
    _total_created = 0

    def __init__(self, conn_id: int):
        self.conn_id = conn_id
        self._is_closed = False
        with self._counter_lock:
            SimulatedDBConnection._total_created += 1
            SimulatedDBConnection._active_connections += 1

    def cursor(self, *args, **kwargs):
        if self._is_closed:
            raise RuntimeError(f"Cannot create cursor on closed connection {self.conn_id}")
        return SimulatedDBCursor(self)

    def ping(self, reconnect=True):
        if self._is_closed:
            raise RuntimeError(f"Ping failed on closed connection {self.conn_id}")
        return True

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        if not self._is_closed:
            self._is_closed = True
            with self._counter_lock:
                SimulatedDBConnection._active_connections -= 1


class SimulatedDBCursor:
    """Simulated cursor with configurable latency to induce thread contention."""
    def __init__(self, conn: SimulatedDBConnection):
        self.conn = conn
        self._closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def execute(self, query, params=None):
        if self._closed:
            raise RuntimeError("Cursor is closed")
        # Micro-sleep to simulate database I/O latency and induce thread race conditions
        time.sleep(0.005)
        return 1

    def fetchone(self):
        return {"result": 1, "conn_id": self.conn.conn_id}

    def fetchall(self):
        return [{"result": 1, "conn_id": self.conn.conn_id}]

    def close(self):
        self._closed = True


class EmpiricalConnectionPoolStressTest(unittest.TestCase):
    """Stress tests verifying thread safety, connection reuse, and deadlock absence."""

    def setUp(self):
        close_db_pool()
        SimulatedDBConnection._active_connections = 0
        SimulatedDBConnection._total_created = 0
        self.created_conns = []
        self.lock = threading.Lock()

    def tearDown(self):
        close_db_pool()

    def _simulated_connect_factory(self, *args, **kwargs):
        with self.lock:
            cid = len(self.created_conns) + 1
            conn = SimulatedDBConnection(cid)
            self.created_conns.append(conn)
            return conn

    def test_challenge_1_10_concurrent_threads_pool_checkout_checkin(self):
        """CHALLENGE 1: 10 concurrent threads simultaneously checkout and checkin connections.
        
        Stress parameters:
        - 10 concurrent worker threads
        - 20 iterations per thread = 200 simultaneous checkout/checkin cycles
        - Strict timeout of 10.0 seconds to catch deadlocks
        """
        print("\n--- [CHALLENGE 1A] 10 Concurrent Threads Pool Checkout/Checkin ---")
        num_threads = 10
        iterations_per_thread = 20
        total_ops = num_threads * iterations_per_thread

        with patch("database.connection.pymysql.connect", side_effect=self._simulated_connect_factory):
            # Initialize pool with maxconnections=20, blocking=True
            init_db_pool(reset=True, maxconnections=20, maxcached=10, mincached=0, blocking=True)

            results = []
            errors = []
            start_time = time.time()

            def worker_task(thread_id: int):
                thread_successes = 0
                for i in range(iterations_per_thread):
                    try:
                        conn = get_db_connection()
                        with conn.cursor() as cur:
                            cur.execute("SELECT %s as thread, %s as iter", (thread_id, i))
                            row = cur.fetchone()
                            self.assertIsNotNone(row)
                        conn.commit()
                        conn.close()
                        thread_successes += 1
                    except Exception as e:
                        errors.append((thread_id, i, e))
                return thread_successes

            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(worker_task, tid) for tid in range(num_threads)]
                for future in as_completed(futures):
                    results.append(future.result())

            elapsed = time.time() - start_time
            print(f"  * Completed {sum(results)}/{total_ops} operations across {num_threads} threads in {elapsed:.3f}s")
            print(f"  * Total underlying connections created: {len(self.created_conns)}")
            print(f"  * Errors recorded: {len(errors)}")

            # Assertions
            self.assertEqual(len(errors), 0, f"Encountered thread errors during pool checkout: {errors}")
            self.assertEqual(sum(results), total_ops, "Not all iterations completed successfully!")
            self.assertLess(elapsed, 10.0, "Deadlock or severe contention occurred (exceeded 10s timeout)")
            # Pool must reuse connections: total created must be <= 20 despite 200 checkouts
            self.assertLessEqual(len(self.created_conns), 20, "Connection pool failed to reuse connections!")

    def test_challenge_1b_heavy_contention_pool_exhaustion_and_recovery(self):
        """CHALLENGE 1B: Extreme contention where thread count (10) exceeds pool maxconnections (4).
        
        Verifies:
        - Blocking queue semantics under heavy pool pressure
        - Zero deadlocks when 10 threads compete for 4 slots
        - Connections are recycled cleanly without leaking
        """
        print("\n--- [CHALLENGE 1B] 10 Threads Under Severe Contention (Pool Max=4) ---")
        num_threads = 10
        iterations = 10
        total_ops = num_threads * iterations

        with patch("database.connection.pymysql.connect", side_effect=self._simulated_connect_factory):
            # Maxconnections restricted to 4, blocking=True via environment
            with patch.dict(os.environ, {"DB_POOL_MAX_CONNECTIONS": "4", "DB_POOL_MAX_CACHED": "4"}):
                init_db_pool(reset=True)

                errors = []
                completed_ops = 0
                start_time = time.time()

                def constrained_worker(thread_id: int):
                    nonlocal completed_ops
                    for i in range(iterations):
                        try:
                            conn = get_db_connection()
                            with conn.cursor() as cur:
                                cur.execute("SELECT %s", (thread_id,))
                                cur.fetchone()
                            conn.close()
                            completed_ops += 1
                        except Exception as e:
                            errors.append((thread_id, e))

                threads = [threading.Thread(target=constrained_worker, args=(i,)) for i in range(num_threads)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join(timeout=10.0)
                    self.assertFalse(t.is_alive(), "Thread deadlocked waiting for database connection!")

                elapsed = time.time() - start_time
                print(f"  * Completed {completed_ops}/{total_ops} queued operations under 4-connection cap in {elapsed:.3f}s")
                print(f"  * Total physical connections created: {len(self.created_conns)} (must be <= 4)")

                self.assertEqual(len(errors), 0, f"Thread contention produced errors: {errors}")
                self.assertEqual(completed_ops, total_ops)
                self.assertLessEqual(len(self.created_conns), 4, "Pool exceeded maxconnections=4 limit!")


# ============================================================================
# 2. EMPIRICAL CHALLENGE: SESSION REVOCATION ON PASSWORD CHANGE
# ============================================================================
class MockDatabaseState:
    """In-memory realistic relational store simulating users and sessions tables."""
    def __init__(self):
        self.users = {}
        self.sessions = {}
        self.next_session_id = 1
        self.lock = threading.Lock()

    def add_user(self, user_id, email, password, name="Test User", role="user", is_active=1):
        with self.lock:
            self.users[user_id] = {
                "id": user_id,
                "email": email,
                "password_hash": _bcrypt_hash(password),
                "name": name,
                "role": role,
                "is_active": is_active,
            }

    def add_session(self, user_id, token, expires_in_sec=86400 * 7):
        with self.lock:
            sid = self.next_session_id
            self.next_session_id += 1
            expires_at = datetime.datetime.now() + datetime.timedelta(seconds=expires_in_sec)
            self.sessions[token] = {
                "id": sid,
                "user_id": user_id,
                "token": token,
                "expires_at": expires_at,
                "ip_address": "127.0.0.1",
                "user_agent": "EmpiricalTest/1.0",
            }

    def get_connection(self):
        return MockRelationalConnection(self)


class MockRelationalConnection:
    def __init__(self, state: MockDatabaseState):
        self.state = state
        self.is_closed = False

    def cursor(self, *args, **kwargs):
        return MockRelationalCursor(self.state)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        self.is_closed = True


class MockRelationalCursor:
    def __init__(self, state: MockDatabaseState):
        self.state = state
        self.last_result = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def execute(self, query: str, params=()):
        # Normalize all whitespace and newlines for robust SQL matching
        q = " ".join(query.strip().split())
        with self.state.lock:
            if "SELECT u.* FROM sessions s INNER JOIN users u" in q:
                # _auth_get_user_by_session
                token = params[0]
                session = self.state.sessions.get(token)
                if session and session["expires_at"] > datetime.datetime.now():
                    user = self.state.users.get(session["user_id"])
                    if user and user.get("is_active") == 1:
                        self.last_result = copy.deepcopy(user)
                        return 1
                self.last_result = None
                return 0

            elif "SELECT password_hash FROM users WHERE id=%s" in q:
                uid = params[0]
                user = self.state.users.get(uid)
                if user:
                    self.last_result = {"password_hash": user["password_hash"]}
                    return 1
                self.last_result = None
                return 0

            elif "SELECT * FROM users WHERE email=%s" in q:
                email = params[0]
                for user in self.state.users.values():
                    if user["email"] == email and user.get("is_active") == 1:
                        self.last_result = copy.deepcopy(user)
                        return 1
                self.last_result = None
                return 0

            elif "UPDATE users SET password_hash=%s WHERE id=%s" in q:
                new_hash, uid = params[0], params[1]
                if uid in self.state.users:
                    self.state.users[uid]["password_hash"] = new_hash
                self.last_result = None
                return 1

            elif "UPDATE users SET name=%s WHERE id=%s" in q:
                name, uid = params[0], params[1]
                if uid in self.state.users:
                    self.state.users[uid]["name"] = name
                self.last_result = None
                return 1

            elif "DELETE FROM sessions WHERE user_id=%s" in q:
                uid = params[0]
                # Revoke all sessions belonging to uid
                keys_to_delete = [tok for tok, s in self.state.sessions.items() if s["user_id"] == uid]
                for tok in keys_to_delete:
                    del self.state.sessions[tok]
                self.last_result = None
                return len(keys_to_delete)

            elif "DELETE FROM sessions WHERE token=%s" in q:
                tok = params[0]
                if tok in self.state.sessions:
                    del self.state.sessions[tok]
                self.last_result = None
                return 1

            elif "INSERT INTO sessions" in q:
                uid, tok, exp, ip, ua = params
                self.state.sessions[tok] = {
                    "id": self.state.next_session_id,
                    "user_id": uid,
                    "token": tok,
                    "expires_at": datetime.datetime.now() + datetime.timedelta(days=7),
                    "ip_address": ip,
                    "user_agent": ua,
                }
                self.state.next_session_id += 1
                self.last_result = None
                return 1

        self.last_result = None
        return 0

    def fetchone(self):
        return self.last_result

    def fetchall(self):
        if self.last_result is None:
            return []
        return [self.last_result] if isinstance(self.last_result, dict) else self.last_result

    def close(self):
        pass


class EmpiricalSessionRevocationStressTest(unittest.TestCase):
    """Stress tests verifying immediate and complete session revocation on password update."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config.update(TESTING=True)
        cls.client = cls.app.test_client()

    def setUp(self):
        self.db = MockDatabaseState()
        # Seed test users
        self.db.add_user(10, "alice@security.test", "AliceOriginalPassword123")
        self.db.add_user(20, "bob@security.test", "BobOriginalPassword123")

        # Seed multiple active sessions for Alice (desktop, mobile, tablet)
        self.alice_desktop_token = "alice_token_desktop_aaa111"
        self.alice_mobile_token = "alice_token_mobile_bbb222"
        self.alice_tablet_token = "alice_token_tablet_ccc333"
        self.db.add_session(10, self.alice_desktop_token)
        self.db.add_session(10, self.alice_mobile_token)
        self.db.add_session(10, self.alice_tablet_token)

        # Seed active session for Bob
        self.bob_phone_token = "bob_token_phone_zzz999"
        self.db.add_session(20, self.bob_phone_token)

    def test_challenge_2_multi_device_session_invalidation_on_password_change(self):
        """CHALLENGE 2: Confirm password change immediately invalidates ALL active user sessions.
        
        Stress verification:
        1. Pre-condition: Alice has 3 valid sessions on 3 devices; Bob has 1 valid session.
        2. Alice changes password from desktop device.
        3. Confirm desktop session token is rejected.
        4. Confirm mobile and tablet session tokens are rejected.
        5. Confirm protected endpoints (/api/auth/update-profile) return 401 Unauthorized.
        6. Confirm Bob's session remains unaffected (isolation).
        7. Confirm sessions table has 0 rows for Alice.
        """
        print("\n--- [CHALLENGE 2] Multi-Device Session Invalidation on Password Change ---")

        with patch("routes.auth_routes.get_db_connection", side_effect=self.db.get_connection):
            # 1. Verify pre-condition: All 3 of Alice's sessions are valid
            for name, tok in [
                ("Desktop", self.alice_desktop_token),
                ("Mobile", self.alice_mobile_token),
                ("Tablet", self.alice_tablet_token),
            ]:
                self.client.set_cookie("session_token", tok)
                res = self.client.post("/api/auth/check-session")
                data = res.get_json()
                self.assertTrue(data.get("authenticated"), f"Pre-condition failed: Alice {name} session invalid!")

            # Verify Bob session is valid
            self.client.set_cookie("session_token", self.bob_phone_token)
            res_bob = self.client.post("/api/auth/check-session")
            self.assertTrue(res_bob.get_json().get("authenticated"), "Pre-condition failed: Bob session invalid!")

            print("  * Pre-condition passed: Alice (3 devices) and Bob (1 device) actively authenticated.")

            # 2. Alice changes password from desktop device
            self.client.set_cookie("session_token", self.alice_desktop_token)
            change_res = self.client.post(
                "/api/auth/change-password",
                json={
                    "old_password": "AliceOriginalPassword123",
                    "new_password": "AliceBrandNewSecurePassword456",
                },
            )
            self.assertEqual(change_res.status_code, 200)
            self.assertTrue(change_res.get_json().get("success"))
            print("  * Password change executed successfully via /api/auth/change-password")

            # 3. Confirm desktop session is rejected
            self.client.set_cookie("session_token", self.alice_desktop_token)
            chk_desktop = self.client.post("/api/auth/check-session")
            self.assertFalse(chk_desktop.get_json().get("authenticated"), "Desktop session remained valid!")

            # 4. Confirm mobile and tablet sessions are also rejected!
            self.client.set_cookie("session_token", self.alice_mobile_token)
            chk_mobile = self.client.post("/api/auth/check-session")
            self.assertFalse(chk_mobile.get_json().get("authenticated"), "Mobile session remained valid!")

            self.client.set_cookie("session_token", self.alice_tablet_token)
            chk_tablet = self.client.post("/api/auth/check-session")
            self.assertFalse(chk_tablet.get_json().get("authenticated"), "Tablet session remained valid!")

            print("  * Verified: All 3 Alice device sessions rejected on /api/auth/check-session")

            # 5. Confirm calling protected endpoint (/api/auth/update-profile) returns 401 Unauthorized
            for tok in [self.alice_desktop_token, self.alice_mobile_token, self.alice_tablet_token]:
                self.client.set_cookie("session_token", tok)
                profile_res = self.client.post("/api/auth/update-profile", json={"name": "Attacker"})
                self.assertEqual(profile_res.status_code, 401, f"Protected endpoint did not return 401 for revoked token {tok}")

            print("  * Verified: Revoked tokens return HTTP 401 on protected endpoint (/api/auth/update-profile)")

            # 6. Confirm database state: 0 active sessions for Alice
            alice_sessions = [s for s in self.db.sessions.values() if s["user_id"] == 10]
            self.assertEqual(len(alice_sessions), 0, f"Alice still has active rows in sessions table: {alice_sessions}")
            print("  * Verified: Database sessions table contains exactly 0 records for Alice")

            # 7. User isolation: Bob's session must remain valid and fully functional
            self.client.set_cookie("session_token", self.bob_phone_token)
            chk_bob = self.client.post("/api/auth/check-session")
            self.assertTrue(chk_bob.get_json().get("authenticated"), "Bob session was inadvertently revoked!")
            bob_profile_res = self.client.post("/api/auth/update-profile", json={"name": "Bob Updated"})
            self.assertEqual(bob_profile_res.status_code, 200, "Bob could not update profile with valid session!")
            print("  * Verified: Bob's session remained untouched and authenticated (isolation confirmed)")

    def test_challenge_2b_php_alias_session_revocation(self):
        """CHALLENGE 2B: Confirm legacy PHP-compat alias /api/api/auth/change_password.php revokes sessions."""
        print("\n--- [CHALLENGE 2B] PHP-Compat Alias Session Revocation ---")
        with patch("routes.auth_routes.get_db_connection", side_effect=self.db.get_connection):
            self.client.set_cookie("session_token", self.alice_desktop_token)
            res = self.client.post(
                "/api/api/auth/change_password.php",
                json={
                    "old_password": "AliceOriginalPassword123",
                    "new_password": "AliceNewPassword789",
                },
            )
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.get_json().get("success"))

            # Confirm session is deleted
            self.assertNotIn(self.alice_desktop_token, self.db.sessions)
            print("  * Verified: Legacy /api/api/auth/change_password.php revoked sessions correctly")


# ============================================================================
# 3. EMPIRICAL CHALLENGE: RATE LIMITING (FLASK-LIMITER HTTP 429 BLOCKING)
# ============================================================================
class EmpiricalRateLimitingStressTest(unittest.TestCase):
    """Stress tests verifying that rapid login requests trigger HTTP 429 on the 6th attempt."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config.update(TESTING=True)
        cls.client = cls.app.test_client()

    def setUp(self):
        limiter.reset()

    def tearDown(self):
        limiter.reset()

    def test_challenge_3_rapid_requests_login_blocked_on_6th_attempt(self):
        """CHALLENGE 3: Send 6 consecutive rapid requests to /api/auth/login.
        
        Requirements:
        - Requests 1 to 5 pass through rate limiter (HTTP 400/401/503, NOT 429)
        - Request 6 MUST BE BLOCKED with HTTP 429
        - Response MUST contain error="rate_limit_exceeded" and success=False
        - Further consecutive requests (7, 8) must also be blocked with HTTP 429
        """
        print("\n--- [CHALLENGE 3] Rapid Login Rate Limiting (6th Request Blocked) ---")
        client_ip = "198.51.100.42"
        headers = {"X-Forwarded-For": client_ip}
        login_payload = {"email": "victim@example.com", "password": "bruteforce_attempt"}

        responses = []
        for i in range(1, 9):
            res = self.client.post("/api/auth/login", json=login_payload, headers=headers)
            responses.append((i, res.status_code, res.get_json(silent=True)))

        print("  * Consecutive request responses:")
        for attempt, status, body in responses:
            print(f"    - Attempt #{attempt}: HTTP {status} (error: {body.get('error') if body else 'none'})")

        # Verify requests 1-5 were not throttled
        for attempt, status, _ in responses[:5]:
            self.assertNotEqual(status, 429, f"Attempt #{attempt} was prematurely throttled with HTTP 429!")

        # Verify 6th request is strictly blocked with HTTP 429
        sixth_attempt, sixth_status, sixth_body = responses[5]
        self.assertEqual(sixth_attempt, 6)
        self.assertEqual(sixth_status, 429, f"Attempt #6 was NOT blocked with HTTP 429! Status was: {sixth_status}")
        self.assertIsNotNone(sixth_body, "HTTP 429 response body was not JSON!")
        self.assertFalse(sixth_body.get("success"), "429 response did not contain success=False")
        self.assertEqual(sixth_body.get("error"), "rate_limit_exceeded", "429 response did not contain rate_limit_exceeded")

        # Verify attempts 7 and 8 remain blocked
        for attempt, status, _ in responses[6:]:
            self.assertEqual(status, 429, f"Subsequent attempt #{attempt} was not blocked with 429!")

        print("  * Verified: Requests 1-5 passed; Attempt #6 strictly blocked with HTTP 429; Attempts 7-8 blocked.")

    def test_challenge_3b_ip_isolation_and_no_collateral_blocking(self):
        """CHALLENGE 3B: Verify rate limiting isolates by client IP (no cross-IP denial of service)."""
        print("\n--- [CHALLENGE 3B] IP Isolation in Rate Limiting ---")
        ip_attacker = "203.0.113.10"
        ip_innocent = "203.0.113.20"

        # Attacker exhausts quota (6 requests)
        for _ in range(6):
            self.client.post("/api/auth/login", json={"email": "test@test.com", "password": "123"}, headers={"X-Forwarded-For": ip_attacker})

        # Attacker is blocked
        res_attacker = self.client.post("/api/auth/login", json={"email": "test@test.com", "password": "123"}, headers={"X-Forwarded-For": ip_attacker})
        self.assertEqual(res_attacker.status_code, 429)

        # Innocent user from separate IP makes a request: MUST NOT be blocked
        res_innocent = self.client.post("/api/auth/login", json={"email": "test@test.com", "password": "123"}, headers={"X-Forwarded-For": ip_innocent})
        self.assertNotEqual(res_innocent.status_code, 429, "Innocent user was blocked due to shared rate limit bucket!")
        print(f"  * Verified: Attacker IP blocked (HTTP 429), Innocent IP permitted (HTTP {res_innocent.status_code})")

    def test_challenge_3c_options_preflight_does_not_consume_quota(self):
        """CHALLENGE 3C: Confirm CORS OPTIONS preflights are exempt and do not consume rate limit quota."""
        print("\n--- [CHALLENGE 3C] OPTIONS Preflight Exemption ---")
        client_ip = "198.51.100.99"
        headers = {"X-Forwarded-For": client_ip}

        # Send 10 OPTIONS requests
        for _ in range(10):
            res = self.client.options("/api/auth/login", headers=headers)
            self.assertEqual(res.status_code, 200)

        # Immediately send 5 POST requests: should ALL pass
        post_statuses = []
        for _ in range(5):
            res = self.client.post("/api/auth/login", json={"email": "a@b.com", "password": "pass"}, headers=headers)
            post_statuses.append(res.status_code)

        for s in post_statuses:
            self.assertNotEqual(s, 429, "POST request was throttled because OPTIONS consumed quota!")

        # 6th POST request must be throttled
        res_6 = self.client.post("/api/auth/login", json={"email": "a@b.com", "password": "pass"}, headers=headers)
        self.assertEqual(res_6.status_code, 429, "6th POST after OPTIONS was not throttled!")
        print("  * Verified: 10 OPTIONS requests caused 0 quota deduction; 5 POSTs passed; 6th POST throttled.")


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================
if __name__ == "__main__":
    print("=====================================================================")
    print("EMPIRICAL CHALLENGER STRESS HARNESS — MILESTONE M1")
    print("=====================================================================")
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(EmpiricalConnectionPoolStressTest))
    suite.addTest(loader.loadTestsFromTestCase(EmpiricalSessionRevocationStressTest))
    suite.addTest(loader.loadTestsFromTestCase(EmpiricalRateLimitingStressTest))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n=====================================================================")
    print(f"EMPIRICAL STRESS TEST RESULTS: {'SUCCESS / CONFIRMED' if result.wasSuccessful() else 'FAILURE / CHALLENGE_FAILED'}")
    print(f"Tests run: {result.testsRun}, Failures: {len(result.failures)}, Errors: {len(result.errors)}")
    print("=====================================================================")

    sys.exit(0 if result.wasSuccessful() else 1)
