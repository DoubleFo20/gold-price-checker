# routes/historical_routes.py – Historical endpoint wrapper
"""Defines the ``/api/historical`` endpoint and delegates all logic to the
service layer ``services.historical_service``. The response JSON format is
identical to the original implementation.
"""

from flask import Blueprint, jsonify, request

from services.historical_service import get_historical

historical_bp = Blueprint("historical", __name__)

@historical_bp.route("/api/historical")
def historical():
    days = int(request.args.get("days", 365))
    data = get_historical(days)
    status = 200 if "error" not in data else 500
    return jsonify(data), status
