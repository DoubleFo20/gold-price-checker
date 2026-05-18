# services/historical_service.py – Service layer for historical & intraday endpoints

"""Provides thin wrapper functions for the ``/api/historical`` and
``/api/intraday`` routes. The heavy lifting (data fetching, series building,
fallback payload creation) stays in the existing ``services.historical``
module; this file only orchestrates the cache checks, parameter handling and
returns plain Python dicts that the route handlers can ``jsonify``.
"""

import time
import traceback
from datetime import datetime

from flask import request

from services.historical import (
    historical_cache,
    intraday_cache,
    HAVE_YFINANCE,
    build_series_with_world_from_yfinance,
    build_historical_gold_data_free,
    _build_intraday_fallback_payload,
)
from utils.helpers import get_usdthb, to_float

CACHE_DURATION = 30  # seconds – kept for compatibility with original code


def get_historical(days: int = 365) -> dict:
    """Return historical gold price series.
    Mirrors the original ``api_historical`` endpoint logic, preserving the
    JSON structure exactly.
    """
    try:
        # Ensure days is within allowed range (30‑365)
        days = max(30, min(days, 365))
        now = time.time()
        today = datetime.now().date().isoformat()
        # Cached fast‑path
        if (
            historical_cache["data"]
            and historical_cache.get("date") == today
            and now - historical_cache["ts"] < CACHE_DURATION
        ):
            return historical_cache["data"]

        source = ""
        try:
            labels, thai_values, world_values = build_series_with_world_from_yfinance(days=days)
            source = "Yahoo Finance"
        except Exception:
            labels, thai_values = build_historical_gold_data_free(days=days)
            usdthb = get_usdthb()
            factor = usdthb * (15.244 / 31.1035)
            world_values = [v / factor if factor else 0 for v in thai_values]
            source = "Fallback"

        data = {
            "labels": labels,
            "thai_values": [round(v, 2) for v in thai_values],
            "world_values": [round(v, 2) for v in world_values],
            "source": source,
            "updated_at": datetime.now().isoformat(),
        }
        historical_cache.update({"data": data, "ts": now, "date": today})
        return data
    except Exception as e:
        traceback.print_exc()
        return {"error": "ไม่สามารถโหลดข้อมูลย้อนหลังได้", "details": str(e)}


def get_intraday(time_range: str = "1d") -> dict:
    """Return intraday gold price series for a given ``range``.
    Mirrors the original ``api_intraday`` endpoint.
    """
    try:
        now = time.time()
        range_config = {"1d": "5m", "5d": "15m", "1w": "1h", "1mo": "1d"}
        if time_range not in range_config:
            time_range = "1d"
        interval = range_config[time_range]
        cache_key = f"intraday_{time_range}"
        # Cached fast‑path (120 s)
        if cache_key in intraday_cache and now - intraday_cache[cache_key]["ts"] < 120:
            return intraday_cache[cache_key]["data"]

        labels, thai_values, world_values, assoc_values, source = [], [], [], [], ""
        if HAVE_YFINANCE:
            # The original route imported ``yfinance`` lazily; the service keeps that logic.
            try:
                import yfinance as yf
                gld = yf.Ticker("GC=F")
                hist = gld.history(period=time_range, interval=interval)
                if not hist.empty:
                    usdthb = get_usdthb()
                    factor = usdthb * (15.244 / 31.1035) * 0.965
                    for index, row in hist.iterrows():
                        if time_range == "1d":
                            label_str = index.strftime("%H:%M")
                        elif time_range in ["5d", "1w"]:
                            label_str = index.strftime("%d %b %H:%M")
                        else:
                            label_str = index.strftime("%d %b")
                        labels.append(label_str)
                        usd_spot = to_float(row.get("Close")) if hasattr(row, "get") else to_float(row["Close"])
                        if usd_spot is None:
                            continue
                        thb_spot = float(usd_spot) * factor
                        world_values.append(round(float(usd_spot), 2))
                        thai_values.append(round(thb_spot, 2))
                        assoc_values.append(round(thb_spot / 50.0) * 50 - 50)
                    source = f"Yahoo Finance ({time_range})"
                    # Align last bar with real Thai bar sell if available
                    try:
                        real_bar_sell = None
                        from services.gold_price import thai_cache
                        if thai_cache.get("data") and thai_cache["data"].get("bar_sell") is not None:
                            real_bar_sell = float(thai_cache["data"]["bar_sell"])
                        if real_bar_sell and thai_values:
                            basis = real_bar_sell - float(thai_values[-1])
                            thai_values = [round(float(v) + basis, 2) for v in thai_values]
                            assoc_values = [round((float(v) + basis) / 50.0) * 50 - 50 for v in assoc_values]
                            assoc_values[-1] = real_bar_sell
                    except Exception:
                        pass
            except Exception as e:
                print(f"Intraday fetch error for {time_range}: {e}")

        if not labels:
            data = _build_intraday_fallback_payload(time_range, "Synthetic Fallback")
            intraday_cache[cache_key] = {"data": data, "ts": now}
            return data

        if assoc_values and thai_cache["data"] and thai_cache["data"].get("bar_sell"):
            assoc_values[-1] = float(thai_cache["data"]["bar_sell"])

        data = {
            "labels": labels,
            "thai_values": thai_values,
            "world_values": world_values,
            "assoc_values": assoc_values,
            "source": source,
            "updated_at": datetime.now().isoformat(),
        }
        intraday_cache[cache_key] = {"data": data, "ts": now}
        return data
    except Exception as e:
        traceback.print_exc()
        safe_range = time_range if time_range in ("1d", "5d", "1w", "1mo") else "1d"
        data = _build_intraday_fallback_payload(safe_range, "Emergency Fallback")
        data["warning"] = str(e)
        key = f"intraday_{safe_range}"
        intraday_cache[key] = {"data": data, "ts": time.time()}
        return data
