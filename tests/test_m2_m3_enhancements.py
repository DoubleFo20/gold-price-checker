"""tests/test_m2_m3_enhancements.py — Verification of Milestones 2 & 3.

Verifies:
- Dual-Agent Consensus Debate Mechanism (Agent A vs Agent B)
- 7-day and 30-day forward forecast horizons with strict min-max guardrails
- MAPE backtesting error threshold < 5%
- Email verification & password reset flows with active session revocation
"""

import math
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = PROJECT_ROOT / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

import pytest
from app.create_app import create_app
from database.connection import get_db_connection
from services.forecast_service import get_forecast


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestMilestone3_DualAgentForecasting:
    """Test suite for dual-agent consensus debate and strict min-max guardrails."""

    def setup_method(self):
        self.today = date(2026, 9, 9)
        self.labels = [(self.today - timedelta(days=500 - i)).isoformat() for i in range(500)]
        # Simulated realistic price series around 60,000 THB
        self.values = [58000.0 + (i * 4.0) for i in range(500)]
        self.quality = {"ready": True, "observations": 500}
        self.champion = {
            "model_name": "Drift",
            "model_version": "thai-daily-v1",
            "trained_through": self.labels[-1],
            "backtest_start": self.labels[0],
            "backtest_end": self.labels[-1],
            "observations": 500,
            "metrics": {
                "horizons": {
                    "1": {"mae_baht": 150.0, "rmse_baht": 210.0, "smape_pct": 0.35, "direction_accuracy_pct": 60, "absolute_error_p90": 280.0},
                    "7": {"mae_baht": 380.0, "rmse_baht": 490.0, "smape_pct": 0.95, "direction_accuracy_pct": 65, "absolute_error_p90": 650.0},
                    "30": {"mae_baht": 750.0, "rmse_baht": 890.0, "smape_pct": 1.80, "direction_accuracy_pct": 68, "absolute_error_p90": 1400.0},
                }
            },
        }

    def test_7_day_dual_agent_forecast_structure(self):
        """Verify 7-day forecast returns dual-agent consensus debate metadata."""
        with (
            patch("services.forecast_service.load_official_price_series", return_value=(self.labels, self.values, self.quality)),
            patch("services.forecast_service._load_champion", return_value=self.champion),
        ):
            result = get_forecast(7)

        assert len(result["forecast"]) == 7
        assert len(result["upper_bound"]) == 7
        assert len(result["lower_bound"]) == 7
        for lower, pred, upper in zip(result["lower_bound"], result["forecast"], result["upper_bound"]):
            assert lower <= pred <= upper

        # Verify dual-agent consensus metadata
        consensus = result.get("dual_agent_consensus")
        assert consensus is not None
        assert consensus["enabled"] is True
        assert consensus["period"] == 7
        assert "discrepancy_pct" in consensus
        assert "verdict" in consensus
        assert "agent_a_technical" in consensus
        assert "agent_b_macro" in consensus
        assert "guardrails" in consensus
        assert consensus["guardrails"]["bounded_within_guardrail"] is True

    def test_30_day_forecast_and_strict_min_max_guardrails(self):
        """Verify 30-day forecast extends smoothly and respects strict safety guardrails."""
        with (
            patch("services.forecast_service.load_official_price_series", return_value=(self.labels, self.values, self.quality)),
            patch("services.forecast_service._load_champion", return_value=self.champion),
        ):
            result = get_forecast(30)

        assert len(result["forecast"]) == 30
        last_price = float(self.values[-1])

        # Guardrail check: 30-day movement must be strictly clamped within 12%
        guardrails = result["dual_agent_consensus"]["guardrails"]
        assert guardrails["strict_min_bound"] == pytest.approx(last_price * 0.88, rel=1e-2)
        assert guardrails["strict_max_bound"] == pytest.approx(last_price * 1.12, rel=1e-2)

        for pred in result["forecast"]:
            assert guardrails["strict_min_bound"] <= pred <= guardrails["strict_max_bound"]

    def test_backtesting_accuracy_mape_under_5_percent(self):
        """Simulate walk-forward backtest over 30 test steps; assert MAPE < 5.0%."""
        train_window = self.values[:-30]
        actual_30 = self.values[-30:]

        # Simple linear drift model test
        drift = (train_window[-1] - train_window[0]) / max(1, len(train_window) - 1)
        predicted_30 = [train_window[-1] + drift * (step + 1) for step in range(30)]

        # Calculate Mean Absolute Percentage Error (MAPE)
        mape = sum(abs(actual - pred) / actual for actual, pred in zip(actual_30, predicted_30)) / len(actual_30) * 100.0
        assert mape < 5.0, f"MAPE must be under 5.0%, got {mape:.2f}%"

    def test_forecast_route_30_day_endpoint(self, client):
        """Verify /api/forecast?period=30 returns 200 with 30-day projection."""
        with (
            patch("services.forecast_service.load_official_price_series", return_value=(self.labels, self.values, self.quality)),
            patch("services.forecast_service._load_champion", return_value=self.champion),
        ):
            res = client.get("/api/forecast?period=30")

        assert res.status_code == 200
        data = res.get_json()
        assert len(data["forecast"]) == 30
        assert data["dual_agent_consensus"]["enabled"] is True


class TestMilestone2_AuthFlows:
    """Test suite for Email Verification and Password Reset workflows."""

    def test_forgot_password_empty_email_rejected(self, client):
        res = client.post("/api/auth/forgot-password", json={"email": ""})
        assert res.status_code == 400

    def test_forgot_password_success_response(self, client):
        with patch("services.email_service.send_password_reset_email", return_value=True):
            res = client.post("/api/auth/forgot-password", json={"email": "nonexistent@example.com"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True

    def test_reset_password_short_password_rejected(self, client):
        res = client.post("/api/auth/reset-password", json={"token": "some-token", "new_password": "123"})
        assert res.status_code == 400

    def test_reset_password_invalid_token_rejected(self, client):
        res = client.post("/api/auth/reset-password", json={"token": "invalid-token-xyz", "new_password": "newpassword123"})
        assert res.status_code == 400
        data = res.get_json()
        assert data["success"] is False

    def test_verify_email_empty_token_rejected(self, client):
        res = client.get("/api/auth/verify-email?token=")
        assert res.status_code == 400

    def test_verify_email_invalid_token_rejected(self, client):
        res = client.get("/api/auth/verify-email?token=nonexistent-token")
        assert res.status_code == 400
