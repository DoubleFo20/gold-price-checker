"""utils/helpers.py — Shared pure-function helpers."""
import os
import time
import requests

try:
    import bcrypt
    HAVE_BCRYPT = True
except Exception:
    HAVE_BCRYPT = False


def to_float(x):
    try:
        return float(str(x).replace(",", "").strip())
    except Exception:
        return None


def normalize_prices(d: dict):
    """Clean and normalise a gold-price dict in-place, returning it."""
    for k in ("bar_buy", "bar_sell", "ornament_buy", "ornament_sell", "today_change"):
        if k in d and d[k] is not None:
            d[k] = to_float(d[k])
    if d.get("bar_buy") and d.get("bar_sell") and d["bar_buy"] > d["bar_sell"]:
        d["bar_buy"], d["bar_sell"] = d["bar_sell"], d["bar_buy"]
    if d.get("ornament_buy") and d.get("ornament_sell") and d["ornament_buy"] > d["ornament_sell"]:
        d["ornament_buy"], d["ornament_sell"] = d["ornament_sell"], d["ornament_buy"]
    return d


def get_usdthb():
    try:
        r = requests.get(
            "https://api.exchangerate.host/latest",
            params={"base": "USD", "symbols": "THB"},
            timeout=10,
        )
        r.raise_for_status()
        return float(r.json()["rates"]["THB"])
    except Exception:
        return 36.85


def _cookie_secure() -> bool:
    from flask import request as _req
    v = (os.getenv("COOKIE_SECURE") or "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    return bool(_req.is_secure)


def _bcrypt_verify(password: str, password_hash: str) -> bool:
    if not HAVE_BCRYPT:
        raise RuntimeError("bcrypt is required for password verification")
    if not password_hash:
        return False
    h = password_hash
    if h.startswith("$2y$"):
        h = "$2b$" + h[4:]
    try:
        return bcrypt.checkpw(password.encode("utf-8"), h.encode("utf-8"))
    except Exception:
        return False


def _bcrypt_hash(password: str) -> str:
    if not HAVE_BCRYPT:
        raise RuntimeError("bcrypt is required for password hashing")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
