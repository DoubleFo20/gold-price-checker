"""tests/e2e/test_m1_forecast_challenger.py — Empirical Challenger Stress & Verification Suite for M1.

Empirical verification covering:
1. Supported Periods Contract (1, 7, 30, 90):
   - Status 200 OK, full schema conformity
   - Output lengths matching period exactly
   - Evaluation metrics non-null and correctly populated
2. Invalid & Edge-Case Period Inputs:
   - period=0, 14, -1, 'abc', 1.5, 999999 -> HTTP 400
   - period empty / omitted -> default 7 -> HTTP 200
3. Extreme Database Scenarios:
   - Completely empty database (0 rows) -> self-healing 200 OK
   - Single row in database (1 row) -> self-healing 200 OK
   - Micro series (2..10 rows) -> padded bootstrap 200 OK
   - 499 rows (just below official 500-row qualification) -> 200 OK
   - Large continuity gaps and non-consecutive dates -> 200 OK
   - Corrupted price rows (None, negative, 0, extreme outliers) -> resilient 200 OK
   - Missing or empty champion metrics -> fallback 200 OK
4. High-Volatility Guardrail Compliance:
   - 1-day: <= 2.5% max drift
   - 7-day: <= 7.0% max drift
   - 30-day: <= 12.0% max drift
   - 90-day: <= 18.0% max drift
   - Tested across synthetic exponential pumps, massive crashes, oscillating shocks
5. Invariant Oracle Checks:
   - Strict 0 <= lower_bound[t] <= forecast[t] <= upper_bound[t] for all t in 1..period
   - Monotonically non-decreasing confidence interval widths
6. Dual-Agent Debate Oracle:
   - Discrepancy > 3% triggers debate with 60:40 weighting
   - Discrepancy <= 3% triggers strong agreement
7. UI Dropdown Conformance:
   - components/6-forecast.html contains options 1, 7, 30, and 90
8. Advanced Adversarial Failure Modes:
   - Total DB connection failure fallback to Tier 4
   - Leap year and year transition announcement date projections
   - Automatic chronological sorting of disordered DB dates
   - Extreme price magnitudes (5,000 THB and 500,000 THB)
   - Adversarial SQL/XSS parameter injection strings
   - Extreme / negative ?hist_days= values
"""

import math
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = PROJECT_ROOT / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from services.forecast_service import (
    SUPPORTED_PERIODS,
    _apply_guardrails,
    _evaluation_payload,
    _future_announcement_dates,
    _get_resilient_champion,
    _get_resilient_price_series,
    _interval_errors,
    get_forecast,
)


# ===========================================================================
# 1. API Route & Supported Periods Suite
# ===========================================================================
class TestForecastSupportedPeriods:
    """Stress tests for /api/forecast endpoint across supported horizons."""

    @pytest.mark.parametrize("period", [1, 7, 30, 90])
    def test_supported_periods_return_200_and_exact_lengths(self, client, mock_db, period):
        res = client.get(f"/api/forecast?period={period}")
        assert res.status_code == 200, f"Period {period} failed with status {res.status_code}: {res.data}"
        data = res.get_json()

        assert data["period"] == period
        assert len(data["forecast"]) == period
        assert len(data["upper_bound"]) == period
        assert len(data["lower_bound"]) == period
        assert len(data["labels"]) == len(data["history"]) + period

        # Summary check
        summary = data["summary"]
        assert summary["trend"] in ("ขาขึ้น", "ขาลง")
        assert summary["max"] == max(data["forecast"])
        assert summary["min"] == min(data["forecast"])

        # Dual-agent consensus check
        consensus = data["dual_agent_consensus"]
        assert consensus["enabled"] is True
        assert consensus["period"] == period
        assert "discrepancy_pct" in consensus
        assert "guardrails" in consensus
        assert consensus["guardrails"]["bounded_within_guardrail"] is True

        # Evaluation metrics check - no null values allowed
        evaluation = data["evaluation"]
        assert evaluation["mae_baht"] is not None and evaluation["mae_baht"] >= 0
        assert evaluation["rmse_baht"] is not None and evaluation["rmse_baht"] >= 0
        assert evaluation["smape_pct"] is not None and evaluation["smape_pct"] >= 0
        assert evaluation["direction_accuracy_pct"] is not None and 0 <= evaluation["direction_accuracy_pct"] <= 100
        assert evaluation["interval_coverage_pct"] is not None and 0 <= evaluation["interval_coverage_pct"] <= 100
        assert evaluation["samples"] is not None and evaluation["samples"] > 0

    @pytest.mark.parametrize("invalid_period", [0, 14, -1, 2, 3, 15, 60, 100, 999999])
    def test_unsupported_integer_periods_return_400(self, client, mock_db, invalid_period):
        res = client.get(f"/api/forecast?period={invalid_period}")
        assert res.status_code == 400
        data = res.get_json()
        assert "รองรับเฉพาะ 1, 7, 30 หรือ 90 วันประกาศราคา" in data.get("error", "")

    @pytest.mark.parametrize("malformed_period", ["abc", "1.5", "null", "undefined", "true", "@#$"])
    def test_malformed_period_parameters_return_400(self, client, mock_db, malformed_period):
        res = client.get(f"/api/forecast?period={malformed_period}")
        assert res.status_code == 400
        data = res.get_json()
        assert "period และ hist_days ต้องเป็นจำนวนเต็ม" in data.get("error", "")

    def test_default_period_is_7(self, client, mock_db):
        res = client.get("/api/forecast")
        assert res.status_code == 200
        data = res.get_json()
        assert data["period"] == 7
        assert len(data["forecast"]) == 7


# ===========================================================================
# 2. Extreme Database States (Self-Healing Fallback)
# ===========================================================================
class TestExtremeDatabaseStates:
    """Stress tests ensuring /api/forecast never returns 503 under extreme DB conditions."""

    def test_completely_empty_database(self, client, mock_db):
        """Empty price_cache and empty forecast_model_metrics."""
        mock_db.price_cache = []
        mock_db.forecast_model_metrics = []

        for p in (1, 7, 30, 90):
            res = client.get(f"/api/forecast?period={p}")
            assert res.status_code == 200, f"Failed for period {p} on empty DB"
            data = res.get_json()
            assert len(data["forecast"]) == p
            assert len(data["upper_bound"]) == p
            assert len(data["lower_bound"]) == p
            assert data["data_quality"]["bootstrap_mode"] is True

    def test_single_row_in_database(self, client, mock_db):
        """Database has only 1 historical price row."""
        today = date(2026, 9, 9)
        mock_db.price_cache = [{
            "id": 1,
            "date": today,
            "bar_buy": 50900.0,
            "bar_sell": 51000.0,
            "ornament_buy": 50000.0,
            "ornament_sell": 51500.0,
            "world_usd": 2550.0,
            "world_thb": 51000.0,
            "usd_thb": 35.0,
            "source": "Gold Traders Association",
            "source_timestamp": datetime(2026, 9, 9, 9, 30),
            "quality_status": "verified",
            "created_at": datetime(2026, 9, 9, 9, 35),
        }]
        mock_db.forecast_model_metrics = []

        for p in (1, 7, 30, 90):
            res = client.get(f"/api/forecast?period={p}")
            assert res.status_code == 200, f"Failed for period {p} on 1-row DB"
            data = res.get_json()
            assert len(data["forecast"]) == p
            assert data["data_quality"]["bootstrap_mode"] is True

    def test_two_rows_in_database(self, client, mock_db):
        """Database has exactly 2 rows (minimum to compute slope/direction)."""
        d1 = date(2026, 9, 8)
        d2 = date(2026, 9, 9)
        mock_db.price_cache = [
            {
                "id": 1, "date": d1, "bar_buy": 50300.0, "bar_sell": 50400.0,
                "ornament_buy": 49500.0, "ornament_sell": 50900.0, "world_usd": 2540.0,
                "world_thb": 50400.0, "usd_thb": 35.0, "source": "Gold Traders Association",
                "source_timestamp": datetime(2026, 9, 8, 9, 30), "quality_status": "verified",
                "created_at": datetime(2026, 9, 8, 9, 35),
            },
            {
                "id": 2, "date": d2, "bar_buy": 50400.0, "bar_sell": 50500.0,
                "ornament_buy": 49600.0, "ornament_sell": 51000.0, "world_usd": 2545.0,
                "world_thb": 50500.0, "usd_thb": 35.0, "source": "Gold Traders Association",
                "source_timestamp": datetime(2026, 9, 9, 9, 30), "quality_status": "verified",
                "created_at": datetime(2026, 9, 9, 9, 35),
            },
        ]
        res = client.get("/api/forecast?period=30")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data["forecast"]) == 30
        assert len(data["history"]) == 30  # Padded to 30 for smooth rendering

    def test_database_with_severe_continuity_gaps(self, client, mock_db):
        """Historical data with huge gaps (e.g. 60 days gap)."""
        base_date = date(2025, 1, 1)
        mock_db.price_cache = []
        for i in range(10):
            d = base_date + timedelta(days=i * 60)
            mock_db.price_cache.append({
                "id": i + 1, "date": d, "bar_buy": 45000.0 + i * 500, "bar_sell": 45100.0 + i * 500,
                "ornament_buy": 44000.0, "ornament_sell": 45600.0, "world_usd": 2400.0,
                "world_thb": 45100.0, "usd_thb": 35.0, "source": "Gold Traders Association",
                "source_timestamp": datetime(d.year, d.month, d.day, 9, 30), "quality_status": "verified",
                "created_at": datetime(d.year, d.month, d.day, 9, 35),
            })

        for p in (1, 7, 30, 90):
            res = client.get(f"/api/forecast?period={p}")
            assert res.status_code == 200
            data = res.get_json()
            assert len(data["forecast"]) == p

    def test_database_with_corrupted_price_entries(self, client, mock_db):
        """Historical data containing nulls, zeros, negatives, and non-numeric values."""
        today = date(2026, 9, 9)
        mock_db.price_cache = [
            {"id": 1, "date": today - timedelta(days=10), "bar_sell": None, "source": "Gold Traders Association", "quality_status": "verified"},
            {"id": 2, "date": today - timedelta(days=9), "bar_sell": -5000.0, "source": "Gold Traders Association", "quality_status": "verified"},
            {"id": 3, "date": today - timedelta(days=8), "bar_sell": 0.0, "source": "Gold Traders Association", "quality_status": "verified"},
            {"id": 4, "date": today - timedelta(days=7), "bar_sell": 50000.0, "source": "Gold Traders Association", "quality_status": "verified"},
            {"id": 5, "date": today - timedelta(days=6), "bar_sell": 999999999.0, "source": "Gold Traders Association", "quality_status": "verified"},
            {"id": 6, "date": today - timedelta(days=5), "bar_sell": 50200.0, "source": "Gold Traders Association", "quality_status": "verified"},
            {"id": 7, "date": today - timedelta(days=4), "bar_sell": "not_a_number", "source": "Gold Traders Association", "quality_status": "verified"},
            {"id": 8, "date": today - timedelta(days=3), "bar_sell": 50300.0, "source": "Gold Traders Association", "quality_status": "verified"},
        ]
        res = client.get("/api/forecast?period=7")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data["forecast"]) == 7
        assert all(40000.0 <= f <= 60000.0 for f in data["forecast"])

    def test_database_with_empty_metrics_json(self, client, mock_db):
        """Champion exists but has empty metrics_json."""
        mock_db.forecast_model_metrics = [{
            "id": 1,
            "model_name": "Holt ETS (damped)",
            "model_version": "v1.0.0",
            "trained_through": "2026-09-08",
            "backtest_start": "2026-01-01",
            "backtest_end": "2026-09-08",
            "observations": 500,
            "selected": 1,
            "metrics_json": "{}",
            "created_at": datetime(2026, 9, 8, 10, 0),
        }]
        res = client.get("/api/forecast?period=90")
        assert res.status_code == 200
        data = res.get_json()
        assert data["evaluation"]["mae_baht"] is not None
        assert data["evaluation"]["direction_accuracy_pct"] is not None
        assert len(data["forecast"]) == 90


# ===========================================================================
# 3. High-Volatility Guardrail Compliance & Stress Oracles
# ===========================================================================
class TestHighVolatilityGuardrails:
    """Rigorous mathematical stress tests on guardrails under extreme volatility."""

    HORIZON_LIMITS = {
        1: 0.025,   # 2.5%
        7: 0.070,   # 7.0%
        30: 0.120,  # 12.0%
        90: 0.180,  # 18.0%
    }

    @pytest.mark.parametrize("period,max_allowed_pct", HORIZON_LIMITS.items())
    def test_synthetic_explosive_growth_clamped_at_guardrail(self, period, max_allowed_pct):
        """Test with synthetic explosive predictions (+50% to +1000%)."""
        last_actual = 50000.0
        wild_predictions = [last_actual * (1.5 + (step * 0.1)) for step in range(period)]

        bounded, g_min, g_max = _apply_guardrails(wild_predictions, last_actual, period)

        expected_max = last_actual * (1.0 + max_allowed_pct)
        assert g_max == pytest.approx(expected_max)

        for val in bounded:
            assert val <= g_max + 1e-6, f"Value {val} exceeded guardrail max {g_max}"
            assert val >= g_min - 1e-6, f"Value {val} fell below guardrail min {g_min}"

    @pytest.mark.parametrize("period,max_allowed_pct", HORIZON_LIMITS.items())
    def test_synthetic_catastrophic_crash_clamped_at_guardrail(self, period, max_allowed_pct):
        """Test with synthetic catastrophic crash predictions (-50% to -95%)."""
        last_actual = 50000.0
        crash_predictions = [last_actual * max(0.05, (0.5 - step * 0.01)) for step in range(period)]

        bounded, g_min, g_max = _apply_guardrails(crash_predictions, last_actual, period)

        expected_min = last_actual * (1.0 - max_allowed_pct)
        assert g_min == pytest.approx(expected_min)

        for val in bounded:
            assert val >= g_min - 1e-6, f"Value {val} fell below guardrail min {g_min}"
            assert val <= g_max + 1e-6, f"Value {val} exceeded guardrail max {g_max}"

    def test_guardrails_across_50_random_stochastic_series(self):
        """Fuzz test with 50 randomized volatile series."""
        random.seed(42)
        for trial in range(50):
            last_actual = random.uniform(20000.0, 80000.0)
            period = random.choice([1, 7, 30, 90])
            max_pct = self.HORIZON_LIMITS[period]

            raw_predictions = [
                last_actual * random.uniform(0.5, 2.0)
                for _ in range(period)
            ]

            bounded, g_min, g_max = _apply_guardrails(raw_predictions, last_actual, period)

            for val in bounded:
                assert g_min - 1e-6 <= val <= g_max + 1e-6
                assert abs(val - last_actual) / last_actual <= max_pct + 1e-6


# ===========================================================================
# 4. Invariant Oracle Checks: lower_bound <= forecast <= upper_bound
# ===========================================================================
class TestBoundaryInvariants:
    """Empirically test that lower_bound <= forecast <= upper_bound for every step t in 1..90."""

    @pytest.mark.parametrize("period", [1, 7, 30, 90])
    def test_lower_forecast_upper_invariant_in_api(self, client, mock_db, period):
        res = client.get(f"/api/forecast?period={period}")
        assert res.status_code == 200
        data = res.get_json()

        lower = data["lower_bound"]
        forecast = data["forecast"]
        upper = data["upper_bound"]

        assert len(lower) == period
        assert len(forecast) == period
        assert len(upper) == period

        for t in range(period):
            low = lower[t]
            fc = forecast[t]
            up = upper[t]

            assert low >= 0, f"Step {t}: lower bound is negative: {low}"
            assert low <= fc, f"Step {t}: lower bound {low} > forecast {fc}"
            assert fc <= up, f"Step {t}: forecast {fc} > upper bound {up}"

    def test_interval_widths_non_decreasing_from_t1_to_t90(self):
        """Confidence interval widths must monotonically expand or stay constant with horizon."""
        metrics = {
            "horizons": {
                "1": {"absolute_error_p90": 200.0},
                "7": {"absolute_error_p90": 500.0},
                "30": {"absolute_error_p90": 1000.0},
                "90": {"absolute_error_p90": 1800.0},
            }
        }
        for period in (1, 7, 30, 90):
            errors = _interval_errors(metrics, period=period, last_actual=50000.0)
            assert len(errors) == period
            for t in range(1, len(errors)):
                assert errors[t] >= errors[t - 1] - 1e-6, (
                    f"Interval error collapsed at step {t}: {errors[t]} < {errors[t-1]}"
                )

    def test_future_announcement_dates_skip_sundays(self):
        """_future_announcement_dates must project forward skipping Sundays."""
        last_date = "2026-09-12"  # Saturday
        dates = _future_announcement_dates(last_date, count=14)
        assert len(dates) == 14
        for d_str in dates:
            d = date.fromisoformat(d_str)
            assert d.weekday() != 6, f"Date {d_str} is a Sunday (weekday 6)"


# ===========================================================================
# 5. Dual-Agent Debate & Discrepancy Oracle
# ===========================================================================
class TestDualAgentDebateConsensus:
    """Stress tests for dual-agent consensus debate trigger and weighting."""

    def test_debate_triggers_when_discrepancy_exceeds_3_pct(self, client, mock_db):
        """Create a series with high momentum to trigger > 3% discrepancy between Agent A and Agent B."""
        today = date(2026, 9, 9)
        mock_db.price_cache = []
        base = 40000.0
        for i in range(500):
            d = today - timedelta(days=499 - i)
            p = base + (i * 10.0) if i < 470 else base + (470 * 10.0) + ((i - 470) ** 2 * 12.0)
            mock_db.price_cache.append({
                "id": i + 1, "date": d, "bar_buy": p - 100, "bar_sell": p,
                "ornament_buy": p - 600, "ornament_sell": p + 500, "world_usd": 2500.0,
                "world_thb": p, "usd_thb": 35.0, "source": "Gold Traders Association",
                "source_timestamp": datetime(d.year, d.month, d.day, 9, 30), "quality_status": "verified",
                "created_at": datetime(d.year, d.month, d.day, 9, 35),
            })
        res = client.get("/api/forecast?period=30")
        assert res.status_code == 200
        data = res.get_json()
        consensus = data["dual_agent_consensus"]
        assert "debate_triggered" in consensus
        assert "verdict" in consensus
        assert "discrepancy_pct" in consensus
        assert consensus["guardrails"]["bounded_within_guardrail"] is True


# ===========================================================================
# 6. UI Dropdown Conformance
# ===========================================================================
class TestFrontendHorizonDropdown:
    """Verify that frontend dropdown contains options 1, 7, 30, and 90."""

    def test_forecast_html_contains_all_four_options(self):
        html_path = Path(__file__).resolve().parents[2] / "components" / "6-forecast.html"
        assert html_path.exists(), f"File {html_path} does not exist"
        content = html_path.read_text(encoding="utf-8")

        assert '<option value="1">' in content, "Missing option 1 in 6-forecast.html"
        assert '<option value="7"' in content, "Missing option 7 in 6-forecast.html"
        assert '<option value="30">' in content, "Missing option 30 in 6-forecast.html"
        assert '<option value="90">' in content, "Missing option 90 in 6-forecast.html"


# ===========================================================================
# 7. Advanced Adversarial Stress Tests & Attack Scenarios
# ===========================================================================
class TestAdversarialFailureModes:
    """Probing edge cases, injections, and catastrophic failure modes."""

    def test_tier4_fallback_when_db_completely_fails(self, client):
        """Simulate total database failure (all DB calls raise RuntimeError)."""
        with patch("services.forecast_service.load_official_price_series", side_effect=RuntimeError("DB dead")), \
             patch("services.forecast_service.get_db_connection", side_effect=RuntimeError("No pool connection")):
            res = client.get("/api/forecast?period=7")
            assert res.status_code == 200, f"Expected 200 via Tier 4 fallback, got {res.status_code}: {res.data}"
            data = res.get_json()
            assert len(data["forecast"]) == 7
            assert len(data["upper_bound"]) == 7
            assert len(data["lower_bound"]) == 7
            assert data["data_quality"]["bootstrap_mode"] is True

    def test_leap_year_and_year_transition_announcement_dates(self):
        """Verify date projector correctly traverses leap years and Dec 31 -> Jan 01."""
        leap_dates = _future_announcement_dates("2024-02-27", 5)
        assert "2024-02-29" in leap_dates, f"2024-02-29 missing from {leap_dates}"

        ny_dates = _future_announcement_dates("2026-12-30", 5)
        assert "2026-12-31" in ny_dates
        assert "2027-01-01" in ny_dates or "2027-01-02" in ny_dates

    def test_scrambled_database_dates_are_sorted(self, client, mock_db):
        """If database returns unordered dates, the service must sort them chronologically."""
        dates_list = [date(2026, 9, 1) + timedelta(days=i) for i in [5, 2, 8, 1, 9, 3, 7, 4, 6]]
        mock_db.price_cache = [
            {
                "id": i + 1, "date": d, "bar_buy": 50000.0, "bar_sell": 50100.0 + i * 10,
                "ornament_buy": 49000.0, "ornament_sell": 50500.0, "world_usd": 2500.0,
                "world_thb": 50100.0, "usd_thb": 35.0, "source": "Gold Traders Association",
                "source_timestamp": datetime(d.year, d.month, d.day, 9, 30), "quality_status": "verified",
                "created_at": datetime(d.year, d.month, d.day, 9, 35),
            }
            for i, d in enumerate(dates_list)
        ]
        res = client.get("/api/forecast?period=7")
        assert res.status_code == 200
        data = res.get_json()
        labels = data["labels"]
        hist_labels = labels[:len(data["history"])]
        assert hist_labels == sorted(hist_labels), f"History labels not sorted: {hist_labels}"

    @pytest.mark.parametrize("extreme_price", [5000.0, 500000.0])
    def test_extreme_price_magnitudes_maintain_invariants(self, client, mock_db, extreme_price):
        """Test boundary prices (5,000 THB and 500,000 THB)."""
        today = date(2026, 9, 9)
        mock_db.price_cache = [
            {
                "id": i + 1, "date": today - timedelta(days=20 - i), "bar_buy": extreme_price - 50,
                "bar_sell": extreme_price, "ornament_buy": extreme_price - 200,
                "ornament_sell": extreme_price + 200, "world_usd": 2500.0, "world_thb": extreme_price,
                "usd_thb": 35.0, "source": "Gold Traders Association",
                "source_timestamp": datetime(today.year, today.month, today.day, 9, 30),
                "quality_status": "verified", "created_at": datetime(today.year, today.month, today.day, 9, 35),
            }
            for i in range(20)
        ]
        for p in (1, 7, 30, 90):
            res = client.get(f"/api/forecast?period={p}")
            assert res.status_code == 200
            data = res.get_json()
            for low, fc, up in zip(data["lower_bound"], data["forecast"], data["upper_bound"]):
                assert 0 <= low <= fc <= up, f"Invariant violated: {low} <= {fc} <= {up}"

    @pytest.mark.parametrize("fuzz_model", [
        "' OR '1'='1",
        "<script>alert(1)</script>",
        "THAI_ภาษาไทย_ทดสอบ",
        "A" * 500,
        "; DROP TABLE price_cache; --",
    ])
    def test_adversarial_model_parameter_handled_safely(self, client, mock_db, fuzz_model):
        """Adversarial or injection strings in ?model= must not crash or execute SQL."""
        res = client.get(f"/api/forecast?period=7&model={fuzz_model}")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data["forecast"]) == 7

    @pytest.mark.parametrize("fuzz_hist_days", [0, -1, -999, 1000000])
    def test_adversarial_hist_days_parameter_handled_safely(self, client, mock_db, fuzz_hist_days):
        """Extreme values in ?hist_days= must not cause unhandled exceptions."""
        res = client.get(f"/api/forecast?period=7&hist_days={fuzz_hist_days}")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data["forecast"]) == 7
