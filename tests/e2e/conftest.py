"""tests/e2e/conftest.py — Global fixtures and in-memory mock database for E2E tests."""
import os
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure api directory is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = PROJECT_ROOT / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Set test environment
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("SECRET_KEY", "test-secret-key-12345")
os.environ.setdefault("LINE_CHANNEL_SECRET", "test-line-channel-secret")
os.environ.setdefault("LINE_CHANNEL_ACCESS_TOKEN", "test-line-access-token")
os.environ.setdefault("JOB_TOKEN", "test-job-runner-token-secret")
os.environ.setdefault("VAPID_PUBLIC_KEY", "test-vapid-public-key-xyz")
os.environ.setdefault("VAPID_PRIVATE_KEY", "test-vapid-private-key-abc")

from utils.helpers import _bcrypt_hash


class InMemoryDatabase:
    """Thread-safe in-memory database simulation for E2E integration and scenario tests."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.users = []
        self.sessions = []
        self.price_alerts = []
        self.price_cache = []
        self.saved_forecasts = []
        self.forecast_model_metrics = []
        self.forecast_predictions = []
        self.email_logs = []
        self._auto_id = {
            "users": 1,
            "sessions": 1,
            "price_alerts": 1,
            "price_cache": 1,
            "saved_forecasts": 1,
            "forecast_model_metrics": 1,
            "forecast_predictions": 1,
            "email_logs": 1,
        }
        self.seed_defaults()

    def seed_defaults(self):
        # Default test user
        pw_hash = _bcrypt_hash("password123")
        self.add_user(
            id=1,
            email="testuser@example.com",
            password_hash=pw_hash,
            name="Test User",
            role="user",
            is_active=1,
            verification_token="123456",
        )
        # Default admin user
        admin_hash = _bcrypt_hash("adminPass123!")
        self.add_user(
            id=2,
            email="admin@example.com",
            password_hash=admin_hash,
            name="System Admin",
            role="admin",
            is_active=1,
            verification_token=None,
        )
        # Default price series (500 days for forecasting qualification)
        today = date(2026, 9, 9)
        base_price = 42000.0
        for i in range(500):
            d = today - timedelta(days=500 - i)
            p = base_price + (i * 5.0)
            self.price_cache.append({
                "id": i + 1,
                "date": d,
                "bar_buy": p - 100.0,
                "bar_sell": p,
                "ornament_buy": p - 600.0,
                "ornament_sell": p + 500.0,
                "world_usd": 2500.0 + (i * 0.5),
                "world_thb": p,
                "usd_thb": 35.50,
                "source": "Gold Traders Association",
                "source_timestamp": datetime(d.year, d.month, d.day, 9, 30),
                "quality_status": "verified",
                "created_at": datetime(d.year, d.month, d.day, 9, 35),
            })
        # Default champion model metrics
        self.forecast_model_metrics.append({
            "id": 1,
            "model_name": "Drift",
            "model_version": "v1.0.0",
            "trained_through": "2026-09-08",
            "backtest_start": "2026-01-01",
            "backtest_end": "2026-09-08",
            "observations": 500,
            "selected": 1,
            "metrics_json": '{"horizons": {"1": {"absolute_error_p90": 150.0, "mae_baht": 80.0, "smape_pct": 0.25}, "7": {"absolute_error_p90": 350.0, "mae_baht": 180.0, "smape_pct": 0.45}, "30": {"absolute_error_p90": 800.0, "mae_baht": 420.0, "smape_pct": 1.1}}}',
            "created_at": datetime(2026, 9, 8, 10, 0),
        })

    def add_user(self, **kwargs):
        if "id" not in kwargs or kwargs["id"] is None:
            kwargs["id"] = self._auto_id["users"]
            self._auto_id["users"] += 1
        else:
            if kwargs["id"] >= self._auto_id["users"]:
                self._auto_id["users"] = kwargs["id"] + 1
        self.users.append(kwargs)
        return kwargs

    def create_session(self, user_id, token, expires_in_seconds=86400 * 7):
        expires_at = datetime.fromtimestamp(int(time.time()) + expires_in_seconds).strftime("%Y-%m-%d %H:%M:%S")
        session = {
            "id": self._auto_id["sessions"],
            "user_id": user_id,
            "token": token,
            "expires_at": expires_at,
            "ip_address": "127.0.0.1",
            "user_agent": "pytest-e2e",
            "created_at": datetime.now(),
        }
        self._auto_id["sessions"] += 1
        self.sessions.append(session)
        return session

    def get_connection(self):
        return MockConnection(self)


class MockCursor:
    """Mock DictCursor operating on InMemoryDatabase."""

    def __init__(self, db: InMemoryDatabase):
        self.db = db
        self.last_results = []
        self.rowcount = 0
        self.lastrowid = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def close(self):
        pass

    def execute(self, query: str, params=None):
        params = params or ()
        q = query.strip()
        q_upper = q.upper()
        self.last_results = []
        self.rowcount = 0

        # Health SELECT 1
        if "SELECT 1" in q_upper:
            self.last_results = [{"ok": 1}]
            self.rowcount = 1
            return 1

        # users count
        if "SELECT COUNT(*) AS C FROM USERS" in q_upper or "SELECT COUNT(*) AS COUNT FROM USERS" in q_upper:
            self.last_results = [{"c": len(self.db.users), "count": len(self.db.users)}]
            self.rowcount = 1
            return 1

        # alerts count
        if "SELECT COUNT(*) AS C FROM PRICE_ALERTS WHERE TRIGGERED=0" in q_upper:
            untriggered = [a for a in self.db.price_alerts if not a.get("triggered")]
            self.last_results = [{"c": len(untriggered)}]
            self.rowcount = 1
            return 1

        # saved_forecasts count
        if "SELECT COUNT(*) AS C FROM SAVED_FORECASTS" in q_upper:
            self.last_results = [{"c": len(self.db.saved_forecasts)}]
            self.rowcount = 1
            return 1

        # SELECT users by email
        if "SELECT * FROM USERS WHERE EMAIL=" in q_upper or "SELECT ID FROM USERS WHERE EMAIL=" in q_upper:
            email = params[0] if params else None
            matches = [u for u in self.db.users if u.get("email") == email]
            if "IS_ACTIVE=1" in q_upper:
                matches = [u for u in matches if u.get("is_active") == 1]
            self.last_results = [dict(m) for m in matches]
            self.rowcount = len(self.last_results)
            return self.rowcount

        # SELECT user by id
        if "SELECT PASSWORD_HASH FROM USERS WHERE ID=" in q_upper or "SELECT * FROM USERS WHERE ID=" in q_upper:
            uid = params[0] if params else None
            matches = [u for u in self.db.users if u.get("id") == uid]
            self.last_results = [dict(m) for m in matches]
            self.rowcount = len(self.last_results)
            return self.rowcount

        # INSERT user
        if q_upper.startswith("INSERT INTO USERS"):
            new_id = self.db._auto_id["users"]
            self.db._auto_id["users"] += 1
            email = params[0]
            pw_hash = params[1]
            name = params[2] if len(params) > 2 else ""
            user = {
                "id": new_id,
                "email": email,
                "password_hash": pw_hash,
                "name": name,
                "role": "user",
                "is_active": 1,
                "verification_token": None,
                "line_user_id": None,
                "line_display_name": None,
                "push_subscription": None,
            }
            self.db.users.append(user)
            self.lastrowid = new_id
            self.rowcount = 1
            return 1

        # UPDATE users password_hash
        if "UPDATE USERS SET PASSWORD_HASH=" in q_upper:
            new_hash = params[0]
            uid = params[1]
            for u in self.db.users:
                if u.get("id") == uid:
                    u["password_hash"] = new_hash
            # In accordance with Project requirements: changing password deletes active sessions
            self.db.sessions = [s for s in self.db.sessions if s.get("user_id") != uid]
            self.rowcount = 1
            return 1

        # UPDATE users name
        if "UPDATE USERS SET NAME=" in q_upper:
            name = params[0]
            uid = params[1]
            for u in self.db.users:
                if u.get("id") == uid:
                    u["name"] = name
            self.rowcount = 1
            return 1

        # UPDATE users verification_token
        if "UPDATE USERS SET VERIFICATION_TOKEN=" in q_upper:
            code = params[0]
            uid = params[1]
            for u in self.db.users:
                if u.get("id") == uid:
                    u["verification_token"] = code
            self.rowcount = 1
            return 1

        # UPDATE users line_user_id
        if "UPDATE USERS SET LINE_USER_ID=" in q_upper:
            lid = params[0]
            dname = params[1]
            uid = params[2]
            for u in self.db.users:
                if u.get("id") == uid:
                    u["line_user_id"] = lid
                    u["line_display_name"] = dname
            self.rowcount = 1
            return 1

        # UPDATE users push_subscription
        if "UPDATE USERS SET PUSH_SUBSCRIPTION=" in q_upper:
            sub = params[0]
            uid = params[1]
            for u in self.db.users:
                if u.get("id") == uid:
                    u["push_subscription"] = sub
            self.rowcount = 1
            return 1

        # INSERT session
        if q_upper.startswith("INSERT INTO SESSIONS"):
            sid = self.db._auto_id["sessions"]
            self.db._auto_id["sessions"] += 1
            session = {
                "id": sid,
                "user_id": params[0],
                "token": params[1],
                "expires_at": params[2],
                "ip_address": params[3] if len(params) > 3 else "127.0.0.1",
                "user_agent": params[4] if len(params) > 4 else "",
            }
            self.db.sessions.append(session)
            self.lastrowid = sid
            self.rowcount = 1
            return 1

        # SELECT session + user JOIN
        if "FROM SESSIONS S" in q_upper and "USERS U" in q_upper:
            token = params[0] if params else None
            session = next((s for s in self.db.sessions if s.get("token") == token), None)
            if session:
                user = next((u for u in self.db.users if u.get("id") == session.get("user_id")), None)
                if user:
                    combined = dict(user)
                    combined["user_id"] = user["id"]
                    combined["expires_at"] = session["expires_at"]
                    self.last_results = [combined]
                    self.rowcount = 1
                    return 1
            self.last_results = []
            self.rowcount = 0
            return 0

        # DELETE FROM sessions
        if q_upper.startswith("DELETE FROM SESSIONS"):
            if "TOKEN=" in q_upper:
                token = params[0]
                self.db.sessions = [s for s in self.db.sessions if s.get("token") != token]
            elif "USER_ID=" in q_upper or "USER_ID = %S" in q_upper:
                uid = params[0]
                self.db.sessions = [s for s in self.db.sessions if s.get("user_id") != uid]
            self.rowcount = 1
            return 1

        # INSERT price_alerts
        if q_upper.startswith("INSERT INTO PRICE_ALERTS"):
            aid = self.db._auto_id["price_alerts"]
            self.db._auto_id["price_alerts"] += 1
            alert = {
                "id": aid,
                "user_id": params[0],
                "target_price": float(params[1]),
                "gold_type": params[2],
                "alert_type": params[3],
                "channel_email": 1,
                "notify_email": params[4],
                "triggered": 0,
                "triggered_at": None,
                "created_at": datetime.now().isoformat(),
            }
            self.db.price_alerts.append(alert)
            self.lastrowid = aid
            self.rowcount = 1
            return 1

        # SELECT price_alerts by notify_email
        if "FROM PRICE_ALERTS WHERE NOTIFY_EMAIL=" in q_upper:
            email = params[0]
            alerts = [dict(a) for a in self.db.price_alerts if a.get("notify_email") == email]
            self.last_results = alerts
            self.rowcount = len(alerts)
            return self.rowcount

        # DELETE FROM price_alerts
        if q_upper.startswith("DELETE FROM PRICE_ALERTS"):
            aid = params[0]
            email = params[1] if len(params) > 1 else None
            self.db.price_alerts = [
                a for a in self.db.price_alerts
                if not (a.get("id") == aid and (email is None or a.get("notify_email") == email))
            ]
            self.rowcount = 1
            return 1

        # SELECT price_cache
        if "FROM PRICE_CACHE" in q_upper:
            if "ORDER BY DATE DESC" in q_upper or "ORDER BY DATE ASC" in q_upper:
                limit = params[0] if params and isinstance(params[0], int) else 500
                rows = list(self.db.price_cache)
                rows.sort(key=lambda r: r["date"], reverse=("ORDER BY DATE DESC" in q_upper))
                self.last_results = [dict(r) for r in rows[:limit]]
                if "ORDER BY DATE ASC" in q_upper and "ORDER BY DATE DESC" in q_upper:
                    # Nested subquery ordering: order ascending overall
                    self.last_results.sort(key=lambda r: r["date"])
                self.rowcount = len(self.last_results)
                return self.rowcount
            if "WHERE DATE=" in q_upper:
                d = params[0]
                matches = [r for r in self.db.price_cache if str(r["date"]) == str(d)]
                self.last_results = [dict(m) for m in matches]
                self.rowcount = len(self.last_results)
                return self.rowcount
            # Generic fallback for price_cache
            self.last_results = [dict(r) for r in self.db.price_cache[:10]]
            self.rowcount = len(self.last_results)
            return self.rowcount

        # SELECT forecast_model_metrics
        if "FROM FORECAST_MODEL_METRICS" in q_upper:
            selected = [m for m in self.db.forecast_model_metrics if m.get("selected") == 1]
            self.last_results = [dict(s) for s in selected]
            self.rowcount = len(self.last_results)
            return self.rowcount

        # SELECT forecast_predictions count
        if "SELECT COUNT(*) AS TOTAL FROM FORECAST_PREDICTIONS" in q_upper:
            self.last_results = [{"total": len(self.db.forecast_predictions)}]
            self.rowcount = 1
            return 1

        # INSERT forecast_predictions
        if q_upper.startswith("INSERT INTO FORECAST_PREDICTIONS"):
            pred = {
                "id": self.db._auto_id["forecast_predictions"],
                "model_name": params[0],
                "model_version": params[1],
                "trained_through": params[2],
                "horizon_step": params[3],
                "projected_target_date": params[4],
                "origin_price": params[5],
                "predicted_price": params[6],
                "lower_bound": params[7],
                "upper_bound": params[8],
            }
            self.db._auto_id["forecast_predictions"] += 1
            self.db.forecast_predictions.append(pred)
            self.rowcount = 1
            return 1

        # Default fallback
        self.last_results = []
        self.rowcount = 0
        return 0

    def fetchone(self):
        return self.last_results[0] if self.last_results else None

    def fetchall(self):
        return list(self.last_results)


class MockConnection:
    """Mock PyMySQL connection."""

    def __init__(self, db: InMemoryDatabase):
        self.db = db
        self.open = True

    def cursor(self, cursorclass=None):
        return MockCursor(self.db)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        self.open = False

    def ping(self, reconnect=True):
        return True


@pytest.fixture(scope="session")
def app():
    """Create and configure a testing Flask app instance."""
    from app.create_app import create_app
    app = create_app()
    app.config.update(TESTING=True, ENV="testing", DEBUG=False)
    return app


@pytest.fixture
def mock_db():
    """Provides a clean in-memory database and patches get_db_connection globally."""
    db = InMemoryDatabase()
    with patch("database.connection.get_db_connection", side_effect=db.get_connection), \
         patch("routes.auth_routes.get_db_connection", side_effect=db.get_connection), \
         patch("routes.alerts.get_db_connection", side_effect=db.get_connection), \
         patch("routes.main.get_db_connection", side_effect=db.get_connection), \
         patch("routes.user_routes.get_db_connection", side_effect=db.get_connection), \
         patch("routes.admin.get_db_connection", side_effect=db.get_connection), \
         patch("routes.webhook.get_db_connection", side_effect=db.get_connection), \
         patch("services.auth.get_db_connection", side_effect=db.get_connection), \
         patch("services.forecast_service.get_db_connection", side_effect=db.get_connection), \
         patch("services.forecast_data.get_db_connection", side_effect=db.get_connection), \
         patch("services.scheduler.get_db_connection", side_effect=db.get_connection):
        yield db


@pytest.fixture
def client(app, mock_db):
    """Provides Flask test client with clean mock database context."""
    from utils.limiter import limiter
    limiter.reset()
    orig_enabled = limiter.enabled
    limiter.enabled = False
    try:
        with app.test_client() as c:
            yield c
    finally:
        limiter.enabled = orig_enabled
        limiter.reset()


