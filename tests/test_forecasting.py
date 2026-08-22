import os
import sys
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = PROJECT_ROOT / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


class ForecastDataQualityTests(unittest.TestCase):
    def test_quality_requires_500_verified_actual_observations(self):
        from services.forecast_data import assess_price_rows

        today = date(2026, 8, 23)
        rows = [
            {"date": today - timedelta(days=499 - index), "bar_sell": 50000 + index}
            for index in range(500)
        ]
        result = assess_price_rows(rows, today=today)
        self.assertTrue(result["ready"])
        self.assertEqual(result["observations"], 500)

        result = assess_price_rows(rows[:-1], today=today)
        self.assertFalse(result["ready"])

    def test_quality_rejects_duplicate_null_and_invalid_prices(self):
        from services.forecast_data import assess_price_rows

        rows = [
            {"date": date(2026, 8, 23), "bar_sell": 50000},
            {"date": date(2026, 8, 23), "bar_sell": None},
            {"date": date(2026, 8, 22), "bar_sell": -1},
        ]
        result = assess_price_rows(rows, today=date(2026, 8, 23))
        self.assertFalse(result["ready"])
        self.assertEqual(result["duplicate_dates"], 1)
        self.assertEqual(result["null_prices"], 1)
        self.assertGreaterEqual(result["invalid_prices"], 2)

    def test_quality_rejects_large_continuity_gap(self):
        from services.forecast_data import assess_price_rows

        today = date(2026, 8, 23)
        rows = [
            {"date": today - timedelta(days=index), "bar_sell": 50000}
            for index in range(499)
        ]
        rows.append({"date": today - timedelta(days=520), "bar_sell": 50000})
        result = assess_price_rows(rows, today=today)
        self.assertFalse(result["ready"])
        self.assertEqual(result["continuity_gaps"], 1)
        self.assertGreater(result["max_gap_days"], 10)

    def test_db_loader_selects_latest_rows_then_returns_ascending(self):
        from services.forecast_data import load_official_price_series

        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [
            {
                "date": date(2026, 8, 22), "bar_sell": 71000,
                "source": "Gold Traders Association", "source_timestamp": datetime(2026, 8, 22, 16),
                "quality_status": "verified",
            },
        ]
        with patch("services.forecast_data.get_db_connection", return_value=connection):
            labels, values, quality = load_official_price_series(require_ready=False)

        sql = cursor.execute.call_args.args[0]
        self.assertIn("ORDER BY date DESC", sql)
        self.assertIn("ORDER BY date ASC", sql)
        self.assertEqual(labels, ["2026-08-22"])
        self.assertEqual(values, [71000.0])
        self.assertFalse(quality["ready"])


class ForecastModelEvaluationTests(unittest.TestCase):
    def test_walk_forward_selects_drift_for_linear_series_deterministically(self):
        from services.forecast_models import ModelSpec, evaluate_models, forecast_drift, forecast_naive

        values = [10000 + (index * 25) for index in range(60)]
        dates = [(date(2026, 1, 1) + timedelta(days=index)).isoformat() for index in range(60)]
        specs = [
            ModelSpec("Baseline", 0, forecast_naive),
            ModelSpec("Drift", 1, forecast_drift),
        ]
        first = evaluate_models(
            values, dates, min_train=20, backtest_observations=20, model_specs=specs,
        )
        second = evaluate_models(
            values, dates, min_train=20, backtest_observations=20, model_specs=specs,
        )
        self.assertEqual(first, second)
        self.assertEqual(first["champion"], "Drift")
        drift = next(item for item in first["models"] if item["name"] == "Drift")
        self.assertEqual(drift["horizons"]["1"]["mae_baht"], 0.0)
        self.assertEqual(drift["horizons"]["7"]["direction_accuracy_pct"], 100.0)

    def test_release_gate_falls_back_to_baseline(self):
        from services.forecast_models import ModelSpec, evaluate_models, forecast_naive

        def bad_forecast(values, steps):
            return [values[-1] * 2] * steps

        values = [50000 + (index % 3) * 10 for index in range(60)]
        dates = [(date(2026, 1, 1) + timedelta(days=index)).isoformat() for index in range(60)]
        report = evaluate_models(
            values,
            dates,
            min_train=20,
            backtest_observations=20,
            model_specs=[
                ModelSpec("Baseline", 0, forecast_naive),
                ModelSpec("Bad", 1, bad_forecast),
            ],
        )
        self.assertEqual(report["champion"], "Baseline")
        bad = next(item for item in report["models"] if item["name"] == "Bad")
        self.assertFalse(bad["passes_release_gate"])

    def test_persist_report_keeps_baseline_and_champion_evidence(self):
        from tools.evaluate_forecast_models import persist_report

        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        report = {
            "champion": "Drift", "model_version": "v1",
            "trained_through": "2026-08-22", "backtest_start": "2026-04-01",
            "backtest_end": "2026-08-22", "observations": 500,
            "models": [
                {"name": "Baseline", "weighted_mae_baht": 100},
                {"name": "Drift", "weighted_mae_baht": 90},
            ],
        }
        with patch("tools.evaluate_forecast_models.get_db_connection", return_value=connection):
            persist_report(report)

        self.assertEqual(cursor.execute.call_count, 3)
        insert_params = [call.args[1] for call in cursor.execute.call_args_list[1:]]
        self.assertEqual([params[0] for params in insert_params], ["Baseline", "Drift"])
        self.assertEqual([params[2] for params in insert_params], [0, 1])
        connection.commit.assert_called_once()


class ForecastServiceTests(unittest.TestCase):
    def setUp(self):
        self.labels = [
            (date(2025, 4, 11) + timedelta(days=index)).isoformat()
            for index in range(500)
        ]
        self.values = [50000 + index for index in range(500)]
        self.quality = {
            "ready": True,
            "observations": 500,
            "source": "Gold Traders Association",
        }
        self.champion = {
            "model_name": "Baseline",
            "model_version": "thai-daily-v1",
            "trained_through": self.labels[-1],
            "backtest_start": self.labels[-120],
            "backtest_end": self.labels[-1],
            "metrics": {
                "horizons": {
                    "1": {
                        "mae_baht": 100, "rmse_baht": 120, "smape_pct": 0.2,
                        "direction_accuracy_pct": 55, "interval_coverage_pct": 90,
                        "samples": 120, "absolute_error_p90": 200,
                    },
                    "7": {
                        "mae_baht": 350, "rmse_baht": 400, "smape_pct": 0.7,
                        "direction_accuracy_pct": 52, "interval_coverage_pct": 88,
                        "samples": 120, "absolute_error_p90": 600,
                    },
                },
            },
        }

    def test_forecast_contract_uses_backtest_metrics_not_r_squared(self):
        from services.forecast_service import get_forecast

        with (
            patch("services.forecast_service.load_official_price_series", return_value=(self.labels, self.values, self.quality)),
            patch("services.forecast_service._load_champion", return_value=self.champion),
        ):
            result = get_forecast(7, "arima", 90)

        self.assertEqual(result["model"], "Baseline")
        self.assertIsNone(result["summary"]["confidence"])
        self.assertEqual(result["evaluation"]["mae_baht"], 350)
        self.assertEqual(result["evaluation"]["direction_accuracy_pct"], 52)
        self.assertEqual(len(result["forecast"]), 7)
        for lower, predicted, upper in zip(
            result["lower_bound"], result["forecast"], result["upper_bound"],
        ):
            self.assertLessEqual(lower, predicted)
            self.assertLessEqual(predicted, upper)
        widths = [upper - lower for lower, upper in zip(result["lower_bound"], result["upper_bound"])]
        self.assertEqual(widths, sorted(widths))


class OfficialImporterTests(unittest.TestCase):
    def test_final_announcement_of_each_day_wins(self):
        from tools.import_gold_history import collapse_to_daily

        rows = collapse_to_daily([
            {
                "AsTime": "2026-08-22 09:00:00", "BL_BuyPrice": "70900",
                "BL_SellPrice": "71000", "OM965_BuyPrice": "70000",
                "OM965_SellPrice": "71500", "GoldSpot": "2500", "BahtPerUSD": "34.50",
            },
            {
                "AsTime": "2026-08-22 16:30:00", "BL_BuyPrice": "71050",
                "BL_SellPrice": "71150", "OM965_BuyPrice": "70100",
                "OM965_SellPrice": "71650", "GoldSpot": "2510", "BahtPerUSD": "34.55",
            },
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["bar_sell"], 71150.0)
        self.assertEqual(rows[0]["quality_status"], "verified")


class BotExchangeTests(unittest.TestCase):
    def test_parser_accepts_nested_official_response_without_fallback(self):
        from services.bot_exchange import parse_daily_rates

        payload = {
            "result": {"data": {"data_detail": [
                {"period": "2026-08-21", "rate": "34.27"},
                {"period": "2026-08-22", "rate": None},
            ]}},
        }
        self.assertEqual(parse_daily_rates(payload), {"2026-08-21": 34.27})

    def test_client_does_not_call_network_without_api_key(self):
        from services.bot_exchange import fetch_daily_rates

        session = MagicMock()
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(fetch_daily_rates("2026-08-21", "2026-08-22", session), {})
        session.get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
