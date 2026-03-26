"""utils/config.py — Environment loading, PROJECT_ROOT, CORS config."""
import os
from urllib.parse import urlparse
from dotenv import load_dotenv


def load_env():
    """Call once at app startup (from server.py)."""
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


# Load immediately so that os.getenv() calls in this module work.
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ---------------------------------------------------------------------------
# Project root helpers
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

if not os.path.exists(os.path.join(PROJECT_ROOT, "index.html")):
    _api_dir = os.path.dirname(os.path.dirname(__file__))
    if os.path.exists(os.path.join(_api_dir, "index.html")):
        PROJECT_ROOT = _api_dir
    elif os.path.exists(os.path.join(_api_dir, "static", "index.html")):
        PROJECT_ROOT = os.path.join(_api_dir, "static")

# ---------------------------------------------------------------------------
# Third-party API keys
# ---------------------------------------------------------------------------
CONFIG = {
    "ALPHA_VANTAGE_KEY": os.getenv("ALPHA_VANTAGE_KEY", ""),
    "NEWSAPI_KEY": os.getenv("NEWSAPI_KEY", ""),
}

# ---------------------------------------------------------------------------
# CORS helpers
# ---------------------------------------------------------------------------
def _load_allowed_origins():
    defaults = {
        "http://localhost",
        "http://127.0.0.1",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    }
    raw = os.getenv("FRONTEND_ORIGINS", "")
    configured = {o.strip().rstrip("/") for o in raw.split(",") if o.strip()}
    return defaults | configured


ALLOWED_ORIGINS = _load_allowed_origins()


def _origin_allowed(origin: str) -> bool:
    if not origin:
        return False
    normalized = origin.rstrip("/")
    if normalized in ALLOWED_ORIGINS:
        return True
    try:
        parsed = urlparse(normalized)
    except Exception:
        return False
    return parsed.hostname in {"localhost", "127.0.0.1"}
