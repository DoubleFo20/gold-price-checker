import os
from .base import Config

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    ENV = "production"
    
    # In production, SECRET_KEY must be set securely
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY or SECRET_KEY == "dev-secret-key-replace-in-prod":
        raise ValueError("No SECRET_KEY set for production application")
