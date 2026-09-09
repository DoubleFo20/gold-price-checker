"""utils/limiter.py — Flask-Limiter extension instance and rate-limit helpers."""
import os
from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def get_client_ip_key() -> str:
    """Resolve client IP using trusted remote address to prevent spoofing."""
    return get_remote_address()


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
)


@limiter.request_filter
def _filter_options_requests() -> bool:
    """Exempt CORS preflight OPTIONS requests from rate limits."""
    return request.method == "OPTIONS"
