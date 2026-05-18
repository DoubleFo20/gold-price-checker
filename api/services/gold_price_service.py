# services/gold_price_service.py – Service layer for Thai & World gold price endpoints

"""Provides thin wrapper functions that encapsulate the business logic for
- world gold price (`/api/world-gold-price`)
- Thai gold price (`/api/thai-gold-price`)
These functions are imported by the route handlers and return plain Python
objects (dict) ready to be passed to ``jsonify``.
"""

import time
import traceback
import threading
from datetime import datetime

from services.gold_price import (
    refresh_thai_cache,
    refresh_world_cache,
    thai_cache,
    world_cache,
)
from utils.helpers import to_float, get_usdthb, usd_oz_to_thb_per_baht

CACHE_DURATION = 30  # seconds – kept for compatibility (used only for fallback logic)


def get_world_price() -> dict:
    """Return world gold price data.
    Mirrors the original ``api_world`` endpoint logic, including fallback to the
    cached Thai price when the world sources fail.
    """
    try:
        # Normal path – refresh cache and return fresh data
        data = refresh_world_cache()
        return data
    except Exception as e:
        # Original code printed the error and then attempted fallback
        print(f"WORLD PRICE ERROR: {e}")
        traceback.print_exc()
        # If we have a cached world price, return it (no staleness flag needed here)
        if world_cache.get("data"):
            stale = dict(world_cache["data"])  # shallow copy
            stale["stale"] = True
            return stale
        # Fallback: estimate from Thai price using the helper conversion
        thai_data = thai_cache.get("data") or {}
        if not thai_data.get("bar_sell"):
            thai_data = refresh_thai_cache() or {}
        thai_bar_sell = to_float(thai_data.get("bar_sell"))
        usdthb = get_usdthb()
        factor = (15.244 / 31.1035) * usdthb
        if thai_bar_sell and factor > 0:
            usd_per_oz_est = thai_bar_sell / factor
            data = {
                "price_usd_per_ounce": round(usd_per_oz_est, 2),
                "usdthb": round(usdthb, 4),
                "thb_per_baht_est": round(thai_bar_sell, 2),
                "last_updated": datetime.now().strftime("%H:%M:%S"),
                "estimated": True,
                "source_note": "Estimated from Thai bar sell",
                "source_url": "derived://thai-bar-sell",
            }
            world_cache.update({"data": data, "ts": time.time()})
            return data
        # Emergency fallback values (same constants as original code)
        fallback_thai = to_float((thai_cache.get("data") or {}).get("bar_sell")) or 41500.0
        fallback_usdthb = to_float(get_usdthb()) or 36.85
        fallback_factor = (15.244 / 31.1035) * fallback_usdthb
        fallback_usd = round(fallback_thai / fallback_factor, 2) if fallback_factor else 0.0
        data = {
            "price_usd_per_ounce": fallback_usd,
            "usdthb": round(fallback_usdthb, 4),
            "thb_per_baht_est": round(fallback_thai, 2),
            "last_updated": datetime.now().strftime("%H:%M:%S"),
            "estimated": True,
            "source_note": "Emergency fallback",
            "source_url": "fallback://static-estimate",
        }
        world_cache.update({"data": data, "ts": time.time()})
        return data


def get_thai_price() -> dict:
    """Return Thai gold price data.
    Mirrors the original ``api_thai`` endpoint, including the background daily
    price saver.
    """
    try:
        data = refresh_thai_cache()
        # Start background job (non‑blocking) – same behaviour as original route
        try:
            threading.Thread(target=save_daily_price, daemon=True).start()
        except Exception:
            pass
        return data
    except Exception as e:
        print(f"FATAL ERROR in get_thai_price: {e}")
        traceback.print_exc()
        # Preserve original error response shape
        return {"error": "Internal Server Error in Thai Price API"}
