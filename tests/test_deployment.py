import base64
import hashlib
import hmac
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = PROJECT_ROOT / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


class ProductionApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.environment = patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "FLASK_ENV": "development",
                "SECRET_KEY": "unit-test-secret-key",
                "LINE_CHANNEL_SECRET": "unit-test-line-secret",
            },
            clear=False,
        )
        cls.environment.start()

        from app.create_app import create_app

        cls.app = create_app()
        cls.app.config.update(TESTING=True)
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.environment.stop()

    def test_app_env_selects_production_before_flask_env(self):
        self.assertEqual(self.app.config["ENV"], "production")
        self.assertFalse(self.app.config["DEBUG"])

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ok"])

    def test_database_health_reports_ready(self):
        connection = unittest.mock.MagicMock()
        with patch("routes.main.get_db_connection", return_value=connection):
            response = self.client.get("/health/db")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["database"], "ready")
        connection.close.assert_called_once()

    def test_database_health_hides_connection_error(self):
        with patch(
            "routes.main.get_db_connection",
            side_effect=RuntimeError("private-db-host.example"),
        ):
            response = self.client.get("/health/db")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json(), {
            "database": "unavailable",
            "ok": False,
        })
        self.assertNotIn("private-db-host", response.get_data(as_text=True))

    def test_login_hides_database_connection_error(self):
        with patch(
            "routes.auth_routes.get_db_connection",
            side_effect=RuntimeError("private-db-host.example"),
        ):
            response = self.client.post(
                "/api/api/auth/login.php",
                json={"email": "demo@example.com", "password": "password"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private-db-host", response.get_data(as_text=True))

    def test_database_debug_endpoint_is_hidden_in_production(self):
        response = self.client.get("/api/debug/db")
        self.assertEqual(response.status_code, 404)

    def test_forecast_rejects_unsupported_horizon(self):
        response = self.client.get("/api/forecast?period=14")
        self.assertEqual(response.status_code, 400)

    def test_forecast_reports_not_ready_without_exposing_database_details(self):
        from services.forecast_service import ForecastUnavailableError

        with patch(
            "routes.forecast_routes.get_forecast",
            side_effect=ForecastUnavailableError("official_data_not_ready"),
        ):
            response = self.client.get("/api/forecast?period=7")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["reason"], "official_data_not_ready")
        self.assertNotIn("DB_HOST", response.get_data(as_text=True))

    def test_webhook_rejects_missing_signature(self):
        response = self.client.post("/webhook", data=b"{}", content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_webhook_rejects_invalid_signature(self):
        response = self.client.post(
            "/webhook",
            data=b"{}",
            content_type="application/json",
            headers={"X-Line-Signature": "invalid"},
        )
        self.assertEqual(response.status_code, 400)

    def test_webhook_accepts_valid_signature(self):
        body = b'{"events":[]}'
        digest = hmac.new(
            b"unit-test-line-secret", body, hashlib.sha256,
        ).digest()
        signature = base64.b64encode(digest).decode("utf-8")
        response = self.client.post(
            "/webhook",
            data=body,
            content_type="application/json",
            headers={"X-Line-Signature": signature},
        )
        self.assertEqual(response.status_code, 200)


class NotificationFanOutTests(unittest.TestCase):
    def test_alert_attempts_every_configured_channel(self):
        from services.notification import _deliver_price_alert

        alert = {
            "id": 1,
            "user_id": 7,
            "name": "Demo",
            "email": "demo@example.com",
            "receiver_email": "demo@example.com",
            "line_user_id": "U-test",
            "push_subscription": {"endpoint": "https://push.example.test"},
            "gold_type": "bar",
            "alert_type": "above",
            "target_price": 50000,
        }
        stats = {}

        with (
            patch("services.notification._save_in_app_notification", return_value=True) as save_in_app,
            patch("services.line_service._line_push", return_value=True) as send_line,
            patch("services.notification._send_web_push", return_value=True) as send_push,
            patch("services.email_service.send_alert_email_smtp", return_value=True) as send_email,
        ):
            result = _deliver_price_alert(object(), alert, 51000, stats=stats)

        self.assertTrue(result["notified"])
        self.assertTrue(result["in_app_saved"])
        self.assertTrue(result["line_sent"])
        self.assertTrue(result["push_sent"])
        self.assertTrue(result["email_sent"])
        save_in_app.assert_called_once()
        send_line.assert_called_once()
        send_push.assert_called_once()
        send_email.assert_called_once()
        self.assertEqual(stats["notifications_saved"], 1)
        self.assertEqual(stats["line_sent"], 1)
        self.assertEqual(stats["push_sent"], 1)
        self.assertEqual(stats["email_sent"], 1)

    def test_one_failed_channel_does_not_block_other_channels(self):
        from services.notification import _deliver_price_alert

        alert = {
            "user_id": 7,
            "email": "demo@example.com",
            "line_user_id": "U-test",
            "push_subscription": {"endpoint": "https://push.example.test"},
            "gold_type": "world",
            "alert_type": "below",
            "target_price": 3000,
        }

        with (
            patch("services.notification._save_in_app_notification", return_value=True),
            patch("services.line_service._line_push", return_value=False),
            patch("services.notification._send_web_push", return_value=True) as send_push,
            patch("services.email_service.send_alert_email_smtp", return_value=True) as send_email,
        ):
            result = _deliver_price_alert(object(), alert, 2900)

        self.assertTrue(result["notified"])
        self.assertFalse(result["line_sent"])
        self.assertTrue(result["push_sent"])
        self.assertTrue(result["email_sent"])
        send_push.assert_called_once()
        send_email.assert_called_once()


class DeploymentSchemaTests(unittest.TestCase):
    def test_schema_is_provider_neutral_and_contains_no_seeded_user(self):
        schema = (API_ROOT / "sql" / "goldapidb.sql").read_text(encoding="utf-8")
        normalized = schema.upper()

        self.assertNotIn("CREATE DATABASE", normalized)
        self.assertNotIn("INSERT INTO USERS", normalized)
        self.assertIn("CREATE TABLE IF NOT EXISTS SAVED_FORECASTS", normalized)
        self.assertIn("CREATE TABLE IF NOT EXISTS NOTIFICATIONS", normalized)
        self.assertIn("CREATE TABLE IF NOT EXISTS PASSWORD_RESETS", normalized)
        self.assertIn("ACTUAL_MAX_PRICE", normalized)
        self.assertIn("IS_VERIFIED", normalized)
        self.assertIn("CREATE TABLE IF NOT EXISTS FORECAST_MODEL_METRICS", normalized)
        self.assertIn("CREATE TABLE IF NOT EXISTS FORECAST_PREDICTIONS", normalized)


class DatabaseConnectionTests(unittest.TestCase):
    def test_aiven_ca_enables_verified_tls(self):
        from database.connection import get_db_connection

        environment = {
            "DB_HOST": "mysql.example.test",
            "DB_PORT": "11838",
            "DB_NAME": "defaultdb",
            "DB_USER": "avnadmin",
            "DB_PASSWORD": "test-password",
            "DB_SSL_CA": "/etc/secrets/aiven-ca.pem",
        }
        with (
            patch.dict(os.environ, environment, clear=False),
            patch("database.connection.pymysql.connect") as connect,
        ):
            get_db_connection()

        connect.assert_called_once_with(
            host="mysql.example.test",
            user="avnadmin",
            password="test-password",
            database="defaultdb",
            port=11838,
            cursorclass=connect.call_args.kwargs["cursorclass"],
            ssl={"ca": "/etc/secrets/aiven-ca.pem", "check_hostname": True},
        )


class ClientIpTests(unittest.TestCase):
    def test_forwarded_chain_uses_first_database_safe_address(self):
        from utils.helpers import _client_ip

        class Request:
            headers = {
                "X-Forwarded-For": "2001:db8::1, 198.51.100.20, 10.0.0.1",
            }
            remote_addr = "127.0.0.1"

        self.assertEqual(_client_ip(Request()), "2001:db8::1")


if __name__ == "__main__":
    unittest.main()
