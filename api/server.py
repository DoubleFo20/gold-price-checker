# ===================== server.py =====================
# Entry point for Gunicorn: gunicorn api.server:app
# NOTHING runs at import time except registering blueprints.
# Background jobs are ONLY started in if __name__ == "__main__".

import os
from flask import Flask, request

# Load .env before anything else
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# CORS helpers (no side-effects — just reads env vars)
from utils.config import ALLOWED_ORIGINS, _origin_allowed

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
app = Flask(__name__)


@app.after_request
def after_request(response):
    origin = request.headers.get("Origin", "")
    if _origin_allowed(origin):
        response.headers["Access-Control-Allow-Origin"] = origin.rstrip("/")
        response.headers["Vary"] = "Origin"
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response


# ---------------------------------------------------------------------------
# Register Blueprints (import inside function scope — no top-level side-effects)
# ---------------------------------------------------------------------------
from routes.main import main_bp
from routes.prices import prices_bp
from routes.forecast import forecast_bp
from routes.auth_routes import auth_bp
from routes.alerts import alerts_bp
from routes.user_routes import user_bp
from routes.webhook import webhook_bp
from routes.jobs import jobs_bp

for bp in (main_bp, prices_bp, forecast_bp, auth_bp, alerts_bp, user_bp, webhook_bp, jobs_bp):
    app.register_blueprint(bp)

# ---------------------------------------------------------------------------
# Gunicorn alias — MUST be at module level
# ---------------------------------------------------------------------------
application = app

# ---------------------------------------------------------------------------
# Dev server entry point — background thread ONLY runs here
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import threading
    from scheduler.jobs import unified_background_alert_checker

    if (os.getenv("ENABLE_BACKGROUND_CHECKER", "true").strip().lower() in ("1", "true", "yes", "on")):
        threading.Thread(target=unified_background_alert_checker, daemon=True).start()
        print("✅ Background checker started (dev mode)")
    else:
        print("Background checker disabled (ENABLE_BACKGROUND_CHECKER=false)")

    port = int(os.getenv("PORT", "5000"))
    debug = (os.getenv("APP_DEBUG", "true").strip().lower() in ("1", "true", "yes", "on"))
    app.run(host="0.0.0.0", port=port, debug=debug)

# ===================== End of server.py =====================
