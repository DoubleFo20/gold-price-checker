"""tests/e2e/test_historical_admin_chart.py — Tests for Admin Chart and Yahoo-decoupled historical API."""

import time
from datetime import date, timedelta
from unittest.mock import patch
import pytest


class TestHistoricalAdminChart:
    """Comprehensive test suite for /api/historical and Admin Chart requirements."""

    def test_historical_admin_7days_shape_and_keys(self, client):
        """Admin chart requests ?days=7: response must contain exact keys and shape."""
        res = client.get("/api/historical?days=7")
        assert res.status_code == 200
        data = res.get_json()

        # Required fields for Chart.js admin dashboard
        assert "labels" in data
        assert "thai_values" in data
        assert "world_values" in data
        assert "source" in data
        assert "updated_at" in data

        assert isinstance(data["labels"], list)
        assert isinstance(data["thai_values"], list)
        assert isinstance(data["world_values"], list)
        assert len(data["labels"]) == 7
        assert len(data["thai_values"]) == 7
        assert len(data["world_values"]) == 7
        assert data["source"] in ("Local Database", "Fallback")

    def test_historical_decoupled_from_yfinance(self, client):
        """Historical endpoint must never invoke yfinance methods."""
        with patch("services.historical.yf.Ticker", side_effect=AssertionError("yfinance was called!")):
            res = client.get("/api/historical?days=7")
            assert res.status_code == 200
            data = res.get_json()
            assert len(data["thai_values"]) == 7

    def test_historical_response_latency_under_100ms(self, client):
        """Historical endpoint responds well within 100ms threshold."""
        t0 = time.perf_counter()
        res = client.get("/api/historical?days=7")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert res.status_code == 200
        assert elapsed_ms < 100.0, f"Expected < 100ms, took {elapsed_ms:.2f}ms"

    def test_historical_fallback_smooth_continuity(self, client):
        """When falling back to synthetic baseline, 7-day variation must be realistic (< 5% max swing)."""
        with patch("routes.prices.build_series_from_db", return_value=(None, None)):
            from services.historical import historical_cache
            historical_cache.pop("days_7", None)

            res = client.get("/api/historical?days=7")
            assert res.status_code == 200
            data = res.get_json()
            assert data["source"] == "Fallback"
            vals = data["thai_values"]
            assert len(vals) == 7

            for v in vals:
                assert v > 10000.0, f"Invalid gold price: {v}"

            max_swing = (max(vals) - min(vals)) / min(vals)
            assert max_swing < 0.05, f"7-day fallback swing too wild: {max_swing * 100:.2f}%"

    def test_historical_local_db_priority(self, client):
        """When local database has enough rows, source must be 'Local Database'."""
        today = date(2026, 9, 10)
        mock_labels = [(today - timedelta(days=6 - i)).isoformat() for i in range(7)]
        mock_values = [42000.0 + i * 50.0 for i in range(7)]

        with patch("routes.prices.build_series_from_db", return_value=(mock_labels, mock_values)):
            from services.historical import historical_cache
            historical_cache.pop("days_7", None)

            res = client.get("/api/historical?days=7")
            assert res.status_code == 200
            data = res.get_json()
            assert data["source"] == "Local Database"
            assert data["labels"] == mock_labels
            assert data["thai_values"] == mock_values

    def test_historical_days_boundary_clamping(self, client):
        """Days outside [7, 365] must be clamped appropriately."""
        from services.historical import historical_cache

        for test_days in (-10, 0, 1, 5, 7):
            historical_cache.pop("days_7", None)
            res = client.get(f"/api/historical?days={test_days}")
            assert res.status_code == 200
            data = res.get_json()
            assert len(data["labels"]) == 7
            assert len(data["thai_values"]) == 7

        historical_cache.pop("days_365", None)
        res = client.get("/api/historical?days=999")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data["labels"]) == 365
        assert len(data["thai_values"]) == 365

    def test_historical_invalid_param_returns_400(self, client):
        """Non-integer days parameter returns 400 Bad Request."""
        res = client.get("/api/historical?days=invalid_string")
        assert res.status_code == 400
        assert "days" in res.get_json().get("error", "")

    def test_historical_cache_hit(self, client):
        """Subsequent request within TTL hits cache immediately."""
        res1 = client.get("/api/historical?days=7")
        assert res1.status_code == 200
        t0 = time.perf_counter()
        res2 = client.get("/api/historical?days=7")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert res2.status_code == 200
        assert res1.get_json() == res2.get_json()
        assert elapsed_ms < 20.0
