"""routes/main.py — Core endpoints + static file serving for the frontend."""
import os
from flask import Blueprint, jsonify, request, send_from_directory
from datetime import datetime

main_bp = Blueprint("main", __name__)

# ---------------------------------------------------------------------------
# Resolve the project root (where index.html lives)
# Layout:  gold-price-checker/          ← PROJECT_ROOT
#              index.html
#              js/
#              api/
#                  routes/main.py       ← __file__
# ---------------------------------------------------------------------------
_ROUTES_DIR = os.path.dirname(os.path.abspath(__file__))   # .../api/routes/
_API_DIR    = os.path.dirname(_ROUTES_DIR)                  # .../api/
PROJECT_ROOT = os.path.abspath(os.path.join(_API_DIR, ".."))  # .../gold-price-checker/

# Fallbacks for different Render deploy layouts
if not os.path.exists(os.path.join(PROJECT_ROOT, "index.html")):
    if os.path.exists(os.path.join(_API_DIR, "index.html")):
        PROJECT_ROOT = _API_DIR
    elif os.path.exists(os.path.join(_API_DIR, "static", "index.html")):
        PROJECT_ROOT = os.path.join(_API_DIR, "static")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@main_bp.route("/", methods=["GET"])
def root():
    """Serve frontend index.html — falls back to JSON if not found."""
    index_path = os.path.join(PROJECT_ROOT, "index.html")
    if os.path.exists(index_path):
        return send_from_directory(PROJECT_ROOT, "index.html")
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
    """Serve frontend static assets (js/, img/, components/, css/).
    Falls back to index.html for SPA client-side routing.
    Returns 404 JSON only if index.html also doesn't exist.
    """
    # Security: prevent path traversal
    safe_path = os.path.normpath(path)
    if safe_path.startswith(".."):
        return jsonify(ok=False, message="Forbidden"), 403

    full_path = os.path.join(PROJECT_ROOT, safe_path)
    if os.path.isfile(full_path):
        return send_from_directory(PROJECT_ROOT, safe_path)

    # SPA fallback — serve index.html for unknown client-side routes
    index_path = os.path.join(PROJECT_ROOT, "index.html")
    if os.path.exists(index_path):
        return send_from_directory(PROJECT_ROOT, "index.html")

    return jsonify(ok=False, message="Not Found", path=path), 404
