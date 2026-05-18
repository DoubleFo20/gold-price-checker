# app/create_app.py – Flask application factory
"""Application factory for the Gold Price Checker API.
Provides a `create_app` function that sets up the Flask instance,
loads environment variables, configures CORS, and registers all
blueprints. This pattern enables easy testing and production deployment
with tools like Gunicorn.
"""

import os
from flask import Flask, request
from dotenv import load_dotenv

# Load environment variables early
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# CORS helpers
from utils.config import ALLOWED_ORIGINS, _origin_allowed


def create_app() -> Flask:
    """Create and configure the Flask application.

    Returns:
        Flask: Configured Flask app instance.
    """
    app = Flask(__name__)
    
    # Load configuration
    env = os.getenv("FLASK_ENV", "development").lower()
    if env == "production":
        app.config.from_object("config.production.ProductionConfig")
    else:
        app.config.from_object("config.development.DevelopmentConfig")

    @app.after_request
    def after_request(response):
        """Add CORS headers based on allowed origins."""
        origin = request.headers.get("Origin", "")
        if _origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin.rstrip("/")
            response.headers["Vary"] = "Origin"
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        response.headers.add("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response

    # Register blueprints – imports are inside the factory to avoid circular imports
    from routes.main import main_bp
    from routes.prices import prices_bp
    from routes.forecast_routes import forecast_bp
    from routes.auth_routes import auth_bp
    from routes.alerts import alerts_bp
    from routes.user_routes import user_bp
    from routes.webhook import webhook_bp
    from routes.jobs import jobs_bp
    from routes.admin import admin_bp

    for bp in (
        main_bp,
        prices_bp,
        forecast_bp,
        auth_bp,
        alerts_bp,
        user_bp,
        webhook_bp,
        jobs_bp,
        admin_bp,
    ):
        app.register_blueprint(bp)

    return app
