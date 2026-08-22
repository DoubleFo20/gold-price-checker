# routes/forecast_routes.py – Forecast endpoint wrapper
"""Defines the ``/api/forecast`` and ``/api/forecast/send-email`` endpoints.
All business logic is delegated to ``services.forecast_service``.  Legacy
query parameters remain accepted, while the response includes evidence and
data-quality metadata for the persisted champion model.
"""

from flask import Blueprint, jsonify, request

from services.forecast_service import (
    ForecastUnavailableError,
    get_forecast,
    send_forecast_email,
)

forecast_bp = Blueprint("forecast", __name__)

@forecast_bp.route("/api/forecast", methods=["GET"])
def forecast():
    try:
        period = int(request.args.get("period", 7))
        hist_days = int(request.args.get("hist_days", 365))
    except (TypeError, ValueError):
        return jsonify(error="period และ hist_days ต้องเป็นจำนวนเต็ม"), 400
    if period not in (1, 7):
        return jsonify(error="รองรับเฉพาะ 1 หรือ 7 วันประกาศราคา"), 400
    model_name = str(request.args.get("model", "linear")).lower()
    try:
        return jsonify(get_forecast(period, model_name, hist_days)), 200
    except ForecastUnavailableError as exc:
        return jsonify(
            error=str(exc),
            reason=exc.reason,
            forecast_ready=False,
        ), 503

@forecast_bp.route("/api/forecast/send-email", methods=["POST", "OPTIONS"])
def forecast_send_email():
    if request.method == "OPTIONS":
        return jsonify(success=True)
    payload = request.get_json(force=True) or {}
    result = send_forecast_email(payload)
    # Determine HTTP status based on result
    if result.get("success"):
        status = 200
    elif result.get("message") == "Missing required fields":
        status = 400
    else:
        status = 500
    return jsonify(result), status
