"""services/historical.py — Historical and intraday gold data builders."""
import time
import random
import math
from datetime import datetime, timedelta

from utils.helpers import to_float, get_usdthb
from database.connection import get_db_connection

try:
    import yfinance as yf
    HAVE_YFINANCE = True
except ImportError:
    HAVE_YFINANCE = False

# In-memory caches
historical_cache = {"data": None, "ts": 0, "date": None}
intraday_cache = {}


def build_series_from_db(days=365):
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT date, bar_sell FROM price_cache
                    WHERE bar_sell IS NOT NULL
                    ORDER BY date ASC
                    LIMIT %s
                    """,
                    (days,),
                )
                rows = cursor.fetchall()
            if len(rows) < 10:
                return None, None
            labels = [r["date"].strftime("%Y-%m-%d") if hasattr(r["date"], "strftime") else str(r["date"]) for r in rows]
            values = [float(r["bar_sell"]) for r in rows]
            print(f"✅ Loaded {len(rows)} days of REAL Thai gold data from price_cache")
            return labels, values
        finally:
            conn.close()
    except Exception as e:
        print(f"⚠️ Failed to load from price_cache: {e}")
        return None, None


def build_series_from_yfinance(days=365):
    if not HAVE_YFINANCE:
        raise ImportError("yfinance library is not installed.")
    from services.gold_price import thai_cache
    print("Attempting historical data from Yahoo Finance...")
    gld = yf.Ticker("GLD")
    hist = gld.history(period=f"{days + 35}d")
    if hist.empty:
        raise ValueError("Yahoo Finance returned no data for GLD.")
    hist = hist.tail(days)
    labels = [d.strftime("%Y-%m-%d") for d in hist.index]
    values_usd = [v * 10.0 for v in hist["Close"]]
    usdthb = get_usdthb()
    factor = usdthb * (15.244 / 31.1035)
    values_thb = [v * factor for v in values_usd]
    try:
        if thai_cache["data"] and thai_cache["data"].get("bar_sell"):
            last_th_real = float(thai_cache["data"]["bar_sell"])
            basis = last_th_real - values_thb[-1]
            values_thb = [v + basis for v in values_thb]
    except Exception as e:
        print(f"Could not adjust yfinance data to Thai price: {e}")
    print("Successfully fetched from Yahoo Finance (adjusted to Thai price).")
    return labels, values_thb


def build_series_with_world_from_yfinance(days=365):
    from services.gold_price import thai_cache
    db_labels, db_values = build_series_from_db(days)
    if db_labels and db_values and len(db_values) >= 30:
        usdthb = get_usdthb()
        factor = usdthb * (15.244 / 31.1035) * 0.965
        values_usd = [v / factor * 10.0 for v in db_values]
        return db_labels, db_values, values_usd

    if not HAVE_YFINANCE:
        raise ImportError("yfinance library is not installed.")
    gld = yf.Ticker("GLD")
    hist = gld.history(period=f"{int(days * 1.5)}d")
    if hist.empty:
        raise ValueError("Yahoo Finance returned no data for GLD.")
    hist = hist.tail(days)
    labels = [d.strftime("%Y-%m-%d") for d in hist.index]
    values_usd = [v * 10.0 for v in hist["Close"]]
    usdthb = get_usdthb()
    factor = usdthb * (15.244 / 31.1035) * 0.965
    values_thb = [v * factor for v in values_usd]
    try:
        if thai_cache["data"] and thai_cache["data"].get("bar_sell"):
            last_th_real = float(thai_cache["data"]["bar_sell"])
            basis = last_th_real - values_thb[-1]
            values_thb = [v + basis for v in values_thb]
    except Exception:
        pass
    return labels, values_thb, values_usd


def build_historical_gold_data_free(days=365):
    from services.gold_price import thai_cache
    db_labels, db_values = build_series_from_db(days)
    if db_labels and db_values:
        return db_labels, db_values

    current_thb = 41500.0
    try:
        if thai_cache["data"] and thai_cache["data"].get("bar_sell"):
            current_thb = float(thai_cache["data"]["bar_sell"])
            print(f"Using real Thai market price for synthetic data: {current_thb}")
    except Exception as e:
        print(f"Could not get Thai price, using fallback: {e}")

    labels, values = [], []
    random.seed(42)
    price = current_thb * 0.88
    daily_volatility = current_thb * 0.006
    for i in range(days):
        day = (datetime.now().date() - timedelta(days=days - 1 - i)).isoformat()
        days_remaining = days - i
        mean_reversion = (current_thb - price) / days_remaining * 0.8 if days_remaining > 0 else 0
        random_shock = random.gauss(0, daily_volatility)
        drift = mean_reversion + random_shock
        price = max(current_thb * 0.75, min(current_thb * 1.05, price + drift))
        labels.append(day)
        values.append(round(price, 2))
    if values:
        values[-1] = round(current_thb, 2)
    print(f"Generated {len(values)} days of synthetic data, ending at {values[-1]} baht")
    return labels, values


def _build_intraday_fallback_payload(time_range="1d", source_note="Synthetic Fallback"):
    from services.gold_price import thai_cache
    safe_range = (time_range or "1d").lower()
    if safe_range not in ("1d", "5d", "1w", "1mo"):
        safe_range = "1d"

    base_price = 41500.0
    try:
        if thai_cache.get("data") and thai_cache["data"].get("bar_sell"):
            base_price = float(thai_cache["data"]["bar_sell"])
    except Exception:
        pass

    usdthb = to_float(get_usdthb()) or 36.85
    factor = usdthb * (15.244 / 31.1035) * 0.965

    points_map = {"1d": 96, "5d": 120, "1w": 168, "1mo": 30}
    step_map = {"1d": 5, "5d": 60, "1w": 60, "1mo": 1440}
    points = points_map.get(safe_range, 30)
    step_mins = step_map.get(safe_range, 1440)

    labels, thai_values, world_values, assoc_values = [], [], [], []
    for i in range(points):
        dt = datetime.now() - timedelta(minutes=(points - i) * step_mins)
        if safe_range == "1d":
            lbl = dt.strftime("%H:%M")
        elif safe_range in ["5d", "1w"]:
            lbl = dt.strftime("%d %b %H:%M")
        else:
            lbl = dt.strftime("%d %b")
        labels.append(lbl)
        noise = math.sin(i / 5.0) * 50 + math.cos(i / 2.0) * 20 + random.uniform(-10, 10)
        price_thb = round(base_price + noise, 2)
        thai_values.append(price_thb)
        world_values.append(round(price_thb / factor, 2) if factor else 0)
        assoc_values.append(round(price_thb / 50.0) * 50 - 50)

    if thai_values:
        thai_values[-1] = round(base_price, 2)
    if world_values:
        world_values[-1] = round(base_price / factor, 2) if factor else 0
    if assoc_values:
        assoc_values[-1] = round(base_price / 50.0) * 50 - 50
        try:
            if thai_cache.get("data") and thai_cache["data"].get("bar_sell"):
                assoc_values[-1] = float(thai_cache["data"]["bar_sell"])
        except Exception:
            pass

    return {
        "labels": labels, "thai_values": thai_values, "world_values": world_values,
        "assoc_values": assoc_values,
        "source": f"{source_note} ({safe_range})",
        "updated_at": datetime.now().isoformat(),
    }
