# routes/forecast_routes.py – Forecast endpoint wrapper
"""Defines the ``/api/forecast`` and ``/api/forecast/send-email`` endpoints.
All business logic is delegated to ``services.forecast_service``.
The JSON response format remains exactly the same as before.
"""

from flask import Blueprint, jsonify, request

from services.forecast_service import get_forecast, send_forecast_email

forecast_bp = Blueprint("forecast", __name__)

@forecast_bp.route("/api/forecast", methods=["GET"])
def forecast():
    period = int(request.args.get("period", 7))
    model_name = str(request.args.get("model", "linear")).lower()
    hist_days = int(request.args.get("hist_days", 90))
    result = get_forecast(period, model_name, hist_days)
    status = 200 if "error" not in result else 500
    return jsonify(result), status

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
