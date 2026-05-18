import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

class Config:
    """Base configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-replace-in-prod")
    DEBUG = False
    TESTING = False
    
    # Database
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASS = os.getenv("DB_PASS", "")
    DB_NAME = os.getenv("DB_NAME", "gold_price_checker")
    
    # API Keys
    ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY", "")
    NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    
    # App Settings
    ENABLE_BACKGROUND_CHECKER = os.getenv("ENABLE_BACKGROUND_CHECKER", "true").strip().lower() in ("1", "true", "yes", "on")
