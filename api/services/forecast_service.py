"""Evidence-backed Thai gold forecasting service."""

from __future__ import annotations

import ast
import json
import math
import traceback
from datetime import date, timedelta

from database.connection import get_db_connection
from services.email_service import send_forecast_email_smtp
from services.forecast_data import OFFICIAL_SOURCE, load_official_price_series
from services.forecast_models import (
    MODEL_VERSION,
    ModelSpec,
    forecast_drift,
    forecast_ets,
    forecast_naive,
    make_arima_forecaster,
)


SUPPORTED_PERIODS = (1, 7)


class ForecastUnavailableError(RuntimeError):
    """Raised when trustworthy production forecasting is not ready."""

    def __init__(self, reason: str, message: str = "ข้อมูลจริงยังไม่พร้อมสำหรับการพยากรณ์"):
        super().__init__(message)
        self.reason = reason


def _load_champion() -> dict:
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT model_name, model_version, trained_through, backtest_start,
                       backtest_end, observations, metrics_json
                FROM forecast_model_metrics
                WHERE selected=1
                ORDER BY created_at DESC LIMIT 1
                """
            )
            row = cursor.fetchone()
    except Exception as exc:
        raise ForecastUnavailableError("model_metrics_unavailable") from exc
    finally:
        conn.close()
    if not row:
        raise ForecastUnavailableError("champion_not_selected")
    metrics = row.get("metrics_json")
    if isinstance(metrics, str):
        metrics = json.loads(metrics)
    row["metrics"] = metrics or {}
    return row


def _model_spec(model_name: str) -> ModelSpec:
    if model_name == "Baseline":
        return ModelSpec("Baseline", 0, forecast_naive)
    if model_name == "Drift":
        return ModelSpec("Drift", 1, forecast_drift)
    if model_name == "Holt ETS (damped)":
        return ModelSpec("Holt ETS (damped)", 2, forecast_ets)
    if model_name.startswith("ARIMA"):
        try:
            order = tuple(int(value) for value in ast.literal_eval(model_name[5:]))
            if len(order) != 3:
                raise ValueError
        except Exception as exc:
            raise ForecastUnavailableError("invalid_champion") from exc
        return ModelSpec(model_name, 3, make_arima_forecaster(order))
    raise ForecastUnavailableError("unknown_champion")


def _future_announcement_dates(last_date: str, count: int) -> list[str]:
    """Project display dates by skipping Sundays; verification uses actual observations."""
    cursor = date.fromisoformat(last_date)
    result: list[str] = []
    while len(result) < count:
        cursor += timedelta(days=1)
        if cursor.weekday() == 6:
            continue
        result.append(cursor.isoformat())
    return result


def _interval_errors(metrics: dict) -> tuple[float, float]:
    horizons = metrics.get("horizons") or {}
    try:
        one = float(horizons["1"]["absolute_error_p90"])
        seven = max(one, float(horizons["7"]["absolute_error_p90"]))
        return one, seven
    except (KeyError, TypeError, ValueError) as exc:
        raise ForecastUnavailableError("invalid_model_metrics") from exc


def _evaluation_payload(champion: dict, period: int) -> dict:
    horizon = (champion["metrics"].get("horizons") or {}).get(str(period)) or {}
    return {
        "mae_baht": horizon.get("mae_baht"),
        "rmse_baht": horizon.get("rmse_baht"),
        "smape_pct": horizon.get("smape_pct"),
        "direction_accuracy_pct": horizon.get("direction_accuracy_pct"),
        "interval_coverage_pct": horizon.get("interval_coverage_pct"),
        "samples": horizon.get("samples"),
        "backtest_start": str(champion.get("backtest_start"))[:10],
        "backtest_end": str(champion.get("backtest_end"))[:10],
    }


def get_forecast(period: int = 7, model_name: str = "champion", hist_days: int = 365) -> dict:
    """Forecast one or seven future official announcement observations.

    ``model_name`` and ``hist_days`` remain accepted for compatibility, while
    production always uses the persisted champion and its backtest evidence.
    """
    del model_name, hist_days
    if period not in SUPPORTED_PERIODS:
        raise ValueError("period must be 1 or 7 announcement days")

    try:
        labels, values, quality = load_official_price_series()
    except Exception as exc:
        raise ForecastUnavailableError("official_data_not_ready") from exc
    champion = _load_champion()
    if str(champion.get("trained_through"))[:10] > labels[-1]:
        raise ForecastUnavailableError("champion_newer_than_data")

    spec = _model_spec(champion["model_name"])
    try:
        predictions = [float(value) for value in spec.forecast(values, period)]
    except Exception as exc:
        raise ForecastUnavailableError("champion_fit_failed") from exc
    if len(predictions) != period or any(not math.isfinite(value) or value <= 0 for value in predictions):
        raise ForecastUnavailableError("invalid_prediction")

    error_one, error_seven = _interval_errors(champion["metrics"])
    errors = [
        error_one + (error_seven - error_one) * ((step - 1) / 6.0)
        for step in range(1, period + 1)
    ]
    upper = [round(value + error, 2) for value, error in zip(predictions, errors)]
    lower = [round(max(0.0, value - error), 2) for value, error in zip(predictions, errors)]
    predictions = [round(value, 2) for value in predictions]
    future_labels = _future_announcement_dates(labels[-1], period)
    last_actual = float(values[-1])

    return {
        "labels": labels[-30:] + future_labels,
        "history": values[-30:],
        "forecast": predictions,
        "upper_bound": upper,
        "lower_bound": lower,
        "summary": {
            "trend": "ขาขึ้น" if predictions[-1] >= last_actual else "ขาลง",
            "max": max(predictions),
            "min": min(predictions),
            "confidence": None,
            "source": OFFICIAL_SOURCE,
        },
        "model": champion["model_name"],
        "model_version": champion.get("model_version") or MODEL_VERSION,
        "trained_through": labels[-1],
        "period": period,
        "evaluation": _evaluation_payload(champion, period),
        "data_quality": quality,
        "deprecations": ["model", "hist_days", "summary.confidence"],
        "disclaimer": "ผลประมาณเชิงสถิติ ไม่ใช่คำแนะนำการลงทุน",
    }


def create_canonical_predictions() -> dict:
    """Upsert the daily 1..7-step prediction path for monitoring."""
    try:
        labels, _, _ = load_official_price_series()
        champion = _load_champion()
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*) AS total FROM forecast_predictions
                    WHERE trained_through=%s AND model_version=%s
                    """,
                    (labels[-1], champion["model_version"]),
                )
                existing = int((cursor.fetchone() or {}).get("total") or 0)
        finally:
            conn.close()
        if existing >= 7:
            return {"created": 0, "trained_through": labels[-1]}
    except ForecastUnavailableError:
        raise
    except Exception as exc:
        raise ForecastUnavailableError("canonical_storage_unavailable") from exc

    payload = get_forecast(7)
    origin = float(payload["history"][-1])
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            for step, (target, predicted, lower, upper) in enumerate(
                zip(
                    payload["labels"][-7:], payload["forecast"],
                    payload["lower_bound"], payload["upper_bound"],
                ),
                start=1,
            ):
                cursor.execute(
                    """
                    INSERT INTO forecast_predictions (
                        model_name, model_version, trained_through, horizon_step,
                        projected_target_date, origin_price, predicted_price,
                        lower_bound, upper_bound
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        projected_target_date=VALUES(projected_target_date),
                        origin_price=VALUES(origin_price), predicted_price=VALUES(predicted_price),
                        lower_bound=VALUES(lower_bound), upper_bound=VALUES(upper_bound)
                    """,
                    (
                        payload["model"], payload["model_version"], payload["trained_through"],
                        step, target, origin, predicted, lower, upper,
                    ),
                )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        if "forecast_predictions" in str(exc).lower():
            raise ForecastUnavailableError("prediction_storage_unavailable") from exc
        raise
    finally:
        conn.close()
    return {"created": 7, "trained_through": payload["trained_through"]}


def _sign(value: float) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def verify_canonical_predictions() -> int:
    """Attach the Nth future official observation to each pending prediction."""
    conn = get_db_connection()
    verified = 0
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, trained_through, horizon_step, origin_price, predicted_price
                FROM forecast_predictions
                WHERE verified_at IS NULL
                ORDER BY trained_through, horizon_step LIMIT 200
                """
            )
            pending = cursor.fetchall() or []
            for row in pending:
                cursor.execute(
                    """
                    SELECT date, bar_sell FROM price_cache
                    WHERE date > %s AND source=%s AND quality_status='verified'
                    ORDER BY date ASC LIMIT 1 OFFSET %s
                    """,
                    (row["trained_through"], OFFICIAL_SOURCE, int(row["horizon_step"]) - 1),
                )
                actual_row = cursor.fetchone()
                if not actual_row:
                    continue
                actual = float(actual_row["bar_sell"])
                origin = float(row["origin_price"])
                predicted = float(row["predicted_price"])
                direction_correct = int(_sign(predicted - origin) == _sign(actual - origin))
                cursor.execute(
                    """
                    UPDATE forecast_predictions SET actual_target_date=%s, actual_price=%s,
                        absolute_error=%s, direction_correct=%s, verified_at=NOW()
                    WHERE id=%s
                    """,
                    (
                        actual_row["date"], actual, abs(predicted - actual),
                        direction_correct, row["id"],
                    ),
                )
                verified += 1
        conn.commit()
    except Exception as exc:
        conn.rollback()
        if "forecast_predictions" in str(exc).lower():
            raise ForecastUnavailableError("prediction_storage_unavailable") from exc
        raise
    finally:
        conn.close()
    return verified


def send_forecast_email(payload: dict) -> dict:
    if not payload.get("email") or not payload.get("target_date"):
        return {"success": False, "message": "Missing required fields"}
    try:
        sent = send_forecast_email_smtp(payload)
        if sent:
            return {"success": True, "message": "Forecast email sent"}
        return {"success": False, "message": "Forecast email send failed"}
    except Exception:
        traceback.print_exc()
        return {"success": False, "message": "Forecast email send failed"}
