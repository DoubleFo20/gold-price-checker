"""Deterministic forecasting models and walk-forward evaluation helpers.

The functions in this module do not access the database or the network.  That
makes the model selection evidence reproducible and keeps future observations
out of every training window.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from typing import Callable, Iterable

import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import Holt


MIN_TRAIN_OBSERVATIONS = 365
BACKTEST_OBSERVATIONS = 120
SUPPORTED_HORIZONS = (1, 7)
MIN_REQUIRED_OBSERVATIONS = 500
MODEL_VERSION = "thai-daily-v1"


@dataclass(frozen=True)
class ModelSpec:
    name: str
    complexity: int
    forecast: Callable[[np.ndarray, int], np.ndarray]


def _as_array(values: Iterable[float]) -> np.ndarray:
    result = np.asarray(list(values), dtype=float)
    if result.ndim != 1 or len(result) < 2 or not np.all(np.isfinite(result)):
        raise ValueError("Forecast series must contain finite one-dimensional values.")
    return result


def forecast_naive(values: Iterable[float], steps: int) -> np.ndarray:
    y = _as_array(values)
    return np.repeat(y[-1], steps).astype(float)


def forecast_drift(values: Iterable[float], steps: int) -> np.ndarray:
    y = _as_array(values)
    drift = (y[-1] - y[0]) / max(1, len(y) - 1)
    return np.asarray([y[-1] + drift * step for step in range(1, steps + 1)], dtype=float)


def forecast_ets(values: Iterable[float], steps: int) -> np.ndarray:
    y = _as_array(values)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = Holt(y, damped_trend=True, initialization_method="estimated").fit(optimized=True)
    return np.asarray(result.forecast(steps), dtype=float)


def _select_arima_order(values: np.ndarray) -> tuple[int, int, int]:
    """Choose a small ARIMA order using AIC on training data only."""
    best_order = (1, 1, 0)
    best_aic = math.inf
    for p in range(0, 4):
        for q in range(0, 3):
            if p == 0 and q == 0:
                continue
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    result = ARIMA(values, order=(p, 1, q)).fit()
                if math.isfinite(result.aic) and result.aic < best_aic:
                    best_order, best_aic = (p, 1, q), float(result.aic)
            except Exception:
                continue
    return best_order


def make_arima_forecaster(order: tuple[int, int, int]) -> Callable[[np.ndarray, int], np.ndarray]:
    def _forecast(values: Iterable[float], steps: int) -> np.ndarray:
        y = _as_array(values)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = ARIMA(y, order=order).fit()
        return np.asarray(result.forecast(steps=steps), dtype=float)

    return _forecast


def default_model_specs(initial_training_values: Iterable[float]) -> list[ModelSpec]:
    initial = _as_array(initial_training_values)
    order = _select_arima_order(initial)
    return [
        ModelSpec("Baseline", 0, forecast_naive),
        ModelSpec("Drift", 1, forecast_drift),
        ModelSpec("Holt ETS (damped)", 2, forecast_ets),
        ModelSpec(f"ARIMA{order}", 3, make_arima_forecaster(order)),
    ]


def _direction_correct(last_value: float, predicted: float, actual: float) -> bool:
    return int(np.sign(predicted - last_value)) == int(np.sign(actual - last_value))


def _metric_summary(actual: list[float], predicted: list[float], origins: list[float]) -> dict:
    y = np.asarray(actual, dtype=float)
    p = np.asarray(predicted, dtype=float)
    errors = p - y
    abs_errors = np.abs(errors)
    denominator = np.abs(y) + np.abs(p)
    smape = np.mean(np.where(denominator == 0, 0.0, 200.0 * abs_errors / denominator))
    direction = np.mean([
        _direction_correct(origin, pred, truth)
        for origin, pred, truth in zip(origins, predicted, actual)
    ])
    calibration_end = max(1, int(len(abs_errors) * 0.60))
    interval_error = float(np.quantile(abs_errors[:calibration_end], 0.90))
    coverage_slice = abs_errors[calibration_end:]
    coverage = (
        float(np.mean(coverage_slice <= interval_error) * 100.0)
        if len(coverage_slice)
        else 100.0
    )
    return {
        "samples": int(len(y)),
        "mae_baht": round(float(np.mean(abs_errors)), 4),
        "rmse_baht": round(float(np.sqrt(np.mean(errors ** 2))), 4),
        "smape_pct": round(float(smape), 4),
        "direction_accuracy_pct": round(float(direction * 100.0), 4),
        "absolute_error_p90": round(interval_error, 4),
        "interval_coverage_pct": round(coverage, 4),
    }


def evaluate_models(
    values: Iterable[float],
    dates: Iterable[str],
    *,
    min_train: int = MIN_TRAIN_OBSERVATIONS,
    backtest_observations: int = BACKTEST_OBSERVATIONS,
    model_specs: list[ModelSpec] | None = None,
) -> dict:
    """Run expanding-window pseudo-out-of-sample evaluation.

    The last ``backtest_observations`` actual observations are targets.  For a
    horizon of seven, the training slice ends seven observations before each
    target, so the target can never leak into model fitting or order selection.
    """
    y = _as_array(values)
    labels = [str(value) for value in dates]
    if len(labels) != len(y):
        raise ValueError("Forecast dates and values must have the same length.")
    required = min_train + backtest_observations + max(SUPPORTED_HORIZONS)
    if len(y) < required:
        raise ValueError(f"At least {required} actual observations are required for backtesting.")

    test_start = len(y) - backtest_observations
    initial_training = y[: test_start - max(SUPPORTED_HORIZONS) + 1]
    specs = model_specs or default_model_specs(initial_training)
    report_models: list[dict] = []

    for spec in specs:
        horizon_metrics: dict[str, dict] = {}
        failed = False
        for horizon in SUPPORTED_HORIZONS:
            actual: list[float] = []
            predicted: list[float] = []
            origins: list[float] = []
            for target_index in range(test_start, len(y)):
                origin_index = target_index - horizon
                train = y[: origin_index + 1]
                if len(train) < min_train:
                    continue
                try:
                    value = float(spec.forecast(train, horizon)[horizon - 1])
                except Exception:
                    failed = True
                    break
                if not math.isfinite(value) or value <= 0:
                    failed = True
                    break
                actual.append(float(y[target_index]))
                predicted.append(value)
                origins.append(float(train[-1]))
            if failed or not actual:
                break
            horizon_metrics[str(horizon)] = _metric_summary(actual, predicted, origins)

        if failed or set(horizon_metrics) != {"1", "7"}:
            continue
        weighted_mae = (
            0.60 * horizon_metrics["1"]["mae_baht"]
            + 0.40 * horizon_metrics["7"]["mae_baht"]
        )
        weighted_direction = (
            0.60 * horizon_metrics["1"]["direction_accuracy_pct"]
            + 0.40 * horizon_metrics["7"]["direction_accuracy_pct"]
        )
        report_models.append({
            "name": spec.name,
            "complexity": spec.complexity,
            "weighted_mae_baht": round(weighted_mae, 4),
            "weighted_direction_accuracy_pct": round(weighted_direction, 4),
            "horizons": horizon_metrics,
        })

    baseline = next((item for item in report_models if item["name"] == "Baseline"), None)
    if baseline is None:
        raise ValueError("Baseline evaluation failed.")

    eligible = [baseline]
    for item in report_models:
        if item is baseline:
            continue
        improves_mae = item["weighted_mae_baht"] <= baseline["weighted_mae_baht"] * 0.95
        preserves_direction = (
            item["weighted_direction_accuracy_pct"]
            >= baseline["weighted_direction_accuracy_pct"]
        )
        item["passes_release_gate"] = bool(improves_mae and preserves_direction)
        if item["passes_release_gate"]:
            eligible.append(item)
    baseline["passes_release_gate"] = True

    eligible.sort(key=lambda item: (item["weighted_mae_baht"], item["complexity"]))
    champion = eligible[0]
    for candidate in eligible[1:]:
        relative_gap = abs(candidate["weighted_mae_baht"] - champion["weighted_mae_baht"]) / max(
            champion["weighted_mae_baht"], 1e-9
        )
        if relative_gap <= 0.01 and candidate["complexity"] < champion["complexity"]:
            champion = candidate

    return {
        "model_version": MODEL_VERSION,
        "observations": int(len(y)),
        "backtest_start": labels[test_start],
        "backtest_end": labels[-1],
        "trained_through": labels[-1],
        "selection_policy": "weighted_mae_h1_60_h7_40_with_5pct_naive_gate",
        "champion": champion["name"],
        "models": report_models,
    }


def get_model_spec(model_name: str, values: Iterable[float]) -> ModelSpec:
    for spec in default_model_specs(values):
        if spec.name == model_name:
            return spec
    if model_name == "Baseline":
        return ModelSpec("Baseline", 0, forecast_naive)
    raise ValueError(f"Unknown forecast model: {model_name}")
