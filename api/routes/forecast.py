"""routes/forecast.py — /api/forecast and /api/forecast/send-email."""
import time
import traceback
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from services.gold_price import thai_cache, world_cache
from services.historical import historical_cache, build_series_with_world_from_yfinance, build_historical_gold_data_free, build_series_from_db
from services.email_service import send_forecast_email_smtp
from utils.helpers import to_float

try:
    import numpy as np
    from sklearn.linear_model import LinearRegression
    HAVE_SKLEARN = True
except ImportError:
    HAVE_SKLEARN = False

try:
    from statsmodels.tsa.arima.model import ARIMA
    HAVE_ARIMA = True
except ImportError:
    HAVE_ARIMA = False

forecast_bp = Blueprint("forecast", __name__)


def _sklearn_forecast(recent_values, period):
    model_name = "Linear Regression"
    X_train = np.array(range(len(recent_values))).reshape(-1, 1)
    y_train = np.array(recent_values, dtype=float)
    model = LinearRegression()
    model.fit(X_train, y_train)
    X_future = np.array(range(len(recent_values), len(recent_values) + period)).reshape(-1, 1)
    preds = model.predict(X_future)
    last_actual = float(recent_values[-1])
    last_fitted = model.predict(np.array([[len(recent_values) - 1]]))[0]
    offset = last_actual - last_fitted
    preds = preds + offset
    r2 = model.score(X_train, y_train)
    confidence = max(50.0, min(95.0, r2 * 100))
    residuals = y_train - model.predict(X_train)
    std_err = np.std(residuals)
    upper = (preds + 1.645 * std_err).tolist()
    lower = (preds - 1.645 * std_err).tolist()
    return preds.tolist(), upper, lower, confidence, model_name


@forecast_bp.route("/api/forecast", methods=["GET"])
def api_forecast():
    try:
        period = int(request.args.get("period", 7))
        model_name = str(request.args.get("model", "linear")).lower()
        hist_days = int(request.args.get("hist_days", 90))
        period = max(1, min(period, 90))
        hist_days = max(30, min(hist_days, 365))

        now = time.time()
        today = datetime.now().date().isoformat()
        source = ""

        db_labels, db_values = build_series_from_db(days=365)
        if db_labels and db_values and len(db_values) >= 30:
            hist_labels, hist_values = db_labels, db_values
            source = "price_cache (Real Thai Data)"
        elif historical_cache["data"] and historical_cache.get("date") == today:
            cache_data = historical_cache["data"]
            hist_labels = cache_data.get("labels")
            hist_values = cache_data.get("values") or cache_data.get("thai_values")
            source = "cached"
            if not hist_labels or not hist_values:
                hist_labels, hist_values = None, None
        else:
            try:
                hist_labels, hist_values, _ = build_series_with_world_from_yfinance(days=365)
                source = "Yahoo Finance (Adjusted)"
            except Exception as e:
                print(f"Historical fetch failed: {e}")
                hist_labels, hist_values = build_historical_gold_data_free(days=365)
                source = "Synthetic (Estimated)"
            historical_cache.update({"data": {"labels": hist_labels, "values": hist_values}, "ts": now, "date": today})

        if not hist_labels or not hist_values:
            hist_labels, hist_values = build_historical_gold_data_free(days=365)
            source = source or "Synthetic (Estimated)"

        recent_values = hist_values[-hist_days:]
        if len(recent_values) < 10:
            raise ValueError("Not enough historical data.")

        forecasts, upper_bound, lower_bound, confidence = [], [], [], 70.0
        last_actual = float(recent_values[-1])

        ARIMA_FAILED = True
        if HAVE_ARIMA and len(recent_values) >= 30:
            try:
                model_name = "ARIMA(5,1,0)"
                y = np.array(recent_values, dtype=float)
                arima_model = ARIMA(y, order=(5, 1, 0))
                arima_result = arima_model.fit()
                forecast_result = arima_result.get_forecast(steps=period)
                forecasts = forecast_result.predicted_mean.tolist()
                diff = last_actual - forecasts[0]
                forecasts = [v + (diff * (0.8**i)) for i, v in enumerate(forecasts)]
                conf_int = forecast_result.conf_int(alpha=0.10)
                lower_bound = (conf_int[:, 0] + diff).tolist()
                upper_bound = (conf_int[:, 1] + diff).tolist()
                aic = arima_result.aic
                confidence = max(50.0, min(95.0, 100.0 - abs(aic) / 100.0))
                ARIMA_FAILED = False
            except Exception as arima_err:
                print(f"ARIMA failed: {arima_err}, falling back to sklearn")

        if ARIMA_FAILED:
            if HAVE_SKLEARN:
                forecasts, upper_bound, lower_bound, confidence, model_name = _sklearn_forecast(recent_values, period)
            else:
                raise ValueError("No forecast model available (install statsmodels or scikit-learn)")

        # Sanity clamp
        max_daily_change = 0.015
        clamped_forecasts = []
        for i, p in enumerate(forecasts):
            days_from_now = i + 1
            max_p = last_actual * (1 + max_daily_change * days_from_now)
            min_p = last_actual * (1 - max_daily_change * days_from_now)
            clamped_forecasts.append(max(min_p, min(max_p, p)))
        forecasts = clamped_forecasts

        recent_array = np.array(recent_values, dtype=float)
        recent_deltas = np.diff(recent_array) if len(recent_array) > 1 else np.array([])
        short_momentum = float(np.mean(recent_deltas[-5:])) if len(recent_deltas) >= 5 else (float(np.mean(recent_deltas)) if len(recent_deltas) else 0.0)
        medium_momentum = float(np.mean(recent_deltas[-20:])) if len(recent_deltas) >= 20 else short_momentum
        momentum = (0.7 * short_momentum) + (0.3 * medium_momentum)
        volatility = float(np.std(recent_deltas[-20:])) if len(recent_deltas) >= 5 else (float(np.std(recent_deltas)) if len(recent_deltas) else 0.0)

        raw_weight = 0.88 if period == 1 else 0.74 if period <= 7 else 0.64 if period <= 14 else 0.56
        trend_boost = 1.0 if period == 1 else 1.08 if period <= 7 else 1.16 if period <= 14 else 1.22
        base_band = max(volatility, last_actual * 0.0015)

        smoothed_forecasts, smoothed_upper, smoothed_lower = [], [], []
        for i, p in enumerate(forecasts):
            days_from_now = i + 1
            trend_projection = last_actual + (momentum * days_from_now * trend_boost)
            blend_weight = max(0.35, raw_weight - (0.02 * min(days_from_now, 10)))
            blended = (blend_weight * float(p)) + ((1.0 - blend_weight) * trend_projection)
            max_move = last_actual * (0.006 + (0.0012 * days_from_now))
            clamped_p = max(last_actual - max_move, min(last_actual + max_move, blended))
            smoothed_forecasts.append(clamped_p)
            band = max(base_band * np.sqrt(days_from_now), abs(momentum) * days_from_now * 0.75, last_actual * 0.0025)
            upper_candidate = float(upper_bound[i]) if i < len(upper_bound) else clamped_p
            lower_candidate = float(lower_bound[i]) if i < len(lower_bound) else clamped_p
            smoothed_upper.append(max(clamped_p + band, upper_candidate))
            smoothed_lower.append(max(0.0, min(clamped_p - band, lower_candidate)))

        forecasts = [max(0.0, round(v, 2)) for v in smoothed_forecasts]
        upper_bound = [max(0.0, round(v, 2)) for v in smoothed_upper]
        lower_bound = [max(0.0, round(v, 2)) for v in smoothed_lower]

        today_date = datetime.now().date()
        forecast_labels = [(today_date + timedelta(days=i)).isoformat() for i in range(1, period + 1)]
        trend = "ขาขึ้น" if forecasts[-1] >= recent_values[-1] else "ขาลง"
        response = {
            "labels": hist_labels[-30:] + forecast_labels,
            "history": hist_values[-30:],
            "forecast": forecasts,
            "upper_bound": upper_bound,
            "lower_bound": lower_bound,
            "summary": {"trend": trend, "max": max(forecasts), "min": min(forecasts), "confidence": round(confidence, 1), "source": source},
            "model": model_name,
            "period": period,
        }
        return jsonify(response)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "ไม่สามารถสร้างการพยากรณ์ได้ในขณะนี้", "details": str(e)}), 500


@forecast_bp.route("/api/forecast/send-email", methods=["POST", "OPTIONS"])
def send_forecast_email():
    if request.method == "OPTIONS":
        return jsonify(success=True)
    try:
        payload = request.json or {}
        if not payload.get("email") or not payload.get("target_date"):
            return jsonify(success=False, message="Missing required fields"), 400
        sent = send_forecast_email_smtp(payload)
        if sent:
            return jsonify(success=True, message="Forecast email sent")
        return jsonify(success=False, message="Forecast email send failed"), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, message=str(e)), 500
