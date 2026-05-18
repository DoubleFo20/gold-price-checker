from .base import Config

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    ENV = "development"
    # Overrides for dev
