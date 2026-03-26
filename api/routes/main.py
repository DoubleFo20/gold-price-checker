"""routes/main.py — Core endpoints: /, /ping, /health, /api/test, /api/meta."""
from flask import Blueprint, jsonify, request
from datetime import datetime

main_bp = Blueprint("main", __name__)


@main_bp.route("/", methods=["GET"])
def root():
    return jsonify(ok=True, service="gold-price-checker-api", status="ok"), 200


@main_bp.route("/ping")
def ping():
    return "pong"


@main_bp.route("/api/test", methods=["GET"])
def api_test():
    return jsonify(ok=True, message="api test ok"), 200


@main_bp.route("/api/meta", methods=["GET"])
def api_meta():
    return jsonify(
        ok=True,
        service="gold-price-checker",
        endpoints=[
            "/api/thai-gold-price", "/api/world-gold-price",
            "/api/intraday?range=1d", "/api/historical?days=365",
            "/api/forecast?period=7&model=auto&hist_days=90",
            "/api/jobs/run", "/webhook",
        ],
    )


@main_bp.route("/health", methods=["GET"])
def health():
    return jsonify(ok=True, time=datetime.now().isoformat())


@main_bp.route("/<path:path>", methods=["GET"])
def static_files(path):
    return jsonify(ok=False, message="Not Found", path=path), 404
