"""services/gold_price.py — Thai and world gold price scrapers + in-memory cache."""
import time
import traceback
import re
import concurrent.futures
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from utils.helpers import to_float, normalize_prices, get_usdthb

try:
    import yfinance as yf
    HAVE_YFINANCE = True
except ImportError:
    HAVE_YFINANCE = False

# ---------------------------------------------------------------------------
# In-memory caches (module-level is fine — not import-time side-effects)
# ---------------------------------------------------------------------------
CACHE_DURATION = 30
thai_cache  = {"data": None, "ts": 0}
world_cache = {"data": None, "ts": 0}

HTTP_HEADERS = {"User-Agent": "Mozilla/5.0"}
WORLD_PRICE_MIN = 500.0
WORLD_PRICE_MAX = 10000.0


def _is_valid_world_price(value):
    v = to_float(value)
    return v is not None and WORLD_PRICE_MIN <= v <= WORLD_PRICE_MAX


def usd_oz_to_thb_per_baht(usd, usdthb):
    return usd * (15.244 / 31.1035) * usdthb


# ---------------------------------------------------------------------------
# World spot sources
# ---------------------------------------------------------------------------
def _fetch_world_from_goldprice_org():
    r = requests.get("https://data-asg.goldprice.org/dbXRates/USD", timeout=10, headers=HTTP_HEADERS)
    r.raise_for_status()
    payload = r.json()
    price = to_float(payload.get("items", [{}])[0].get("xauPrice"))
    if not _is_valid_world_price(price):
        raise ValueError(f"goldprice.org returned invalid xauPrice: {price}")
    return float(price)


def _parse_metals_live_payload(payload):
    if isinstance(payload, list) and payload:
        row = payload[-1]
        if isinstance(row, (list, tuple)) and row:
            if len(row) >= 2 and _is_valid_world_price(row[1]):
                return float(row[1])
            if _is_valid_world_price(row[0]):
                return float(row[0])
        if isinstance(row, dict):
            for key in ("gold", "price", "xau", "xauusd"):
                if _is_valid_world_price(row.get(key)):
                    return float(row[key])
        if _is_valid_world_price(row):
            return float(row)
    if isinstance(payload, dict):
        for key in ("gold", "price", "xau", "xauusd"):
            if _is_valid_world_price(payload.get(key)):
                return float(payload[key])
    raise ValueError("metals.live payload format not recognized")


def _fetch_world_from_metals_live():
    endpoints = ["https://api.metals.live/v1/spot/gold", "https://api.metals.live/v1/spot"]
    last_error = None
    for url in endpoints:
        try:
            r = requests.get(url, timeout=10, headers=HTTP_HEADERS)
            r.raise_for_status()
            return _parse_metals_live_payload(r.json())
        except Exception as e:
            last_error = e
    raise last_error or ValueError("metals.live source failed")


def _fetch_world_from_stooq():
    r = requests.get("https://stooq.com/q/l/?s=xauusd&i=d", timeout=10, headers=HTTP_HEADERS)
    r.raise_for_status()
    lines = [line.strip() for line in r.text.splitlines() if line.strip()]
    if len(lines) < 2:
        raise ValueError("stooq returned no CSV rows")
    headers = [h.strip().lower() for h in lines[0].split(",")]
    values = [v.strip() for v in lines[1].split(",")]
    row = dict(zip(headers, values))
    close = to_float(row.get("close"))
    if close is None and len(values) >= 7:
        close = to_float(values[6])
    if not _is_valid_world_price(close):
        raise ValueError(f"stooq close invalid: {close}")
    return float(close)


def _fetch_world_from_fred_lbma():
    r = requests.get(
        "https://fred.stlouisfed.org/graph/fredgraph.csv?id=GOLDAMGBD228NLBM",
        timeout=10, headers=HTTP_HEADERS,
    )
    r.raise_for_status()
    lines = [line.strip() for line in r.text.splitlines() if line.strip()]
    if len(lines) < 2:
        raise ValueError("FRED returned no data")
    for line in reversed(lines[1:]):
        parts = line.split(",")
        if len(parts) < 2 or parts[1].strip() in ("", "."):
            continue
        price = to_float(parts[1])
        if _is_valid_world_price(price):
            return float(price)
    raise ValueError("FRED has no valid latest world gold value")


def _fetch_world_from_yfinance():
    if not HAVE_YFINANCE:
        raise ImportError("yfinance not installed")
    for symbol in ("XAUUSD=X", "GC=F"):
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="5d")
            if hist is not None and not hist.empty:
                price = to_float(hist["Close"].iloc[-1])
                if _is_valid_world_price(price):
                    return float(price)
        except Exception:
            continue
    raise ValueError("Yahoo Finance symbols returned no valid price")


WORLD_SPOT_SOURCES = [
    ("Yahoo Finance", "XAUUSD=X / GC=F", _fetch_world_from_yfinance),
    ("Metals.Live", "https://api.metals.live/v1/spot/gold", _fetch_world_from_metals_live),
    ("GoldPrice.org", "https://data-asg.goldprice.org/dbXRates/USD", _fetch_world_from_goldprice_org),
    ("Stooq", "https://stooq.com/q/l/?s=xauusd&i=d", _fetch_world_from_stooq),
    ("FRED LBMA AM", "https://fred.stlouisfed.org/graph/fredgraph.csv?id=GOLDAMGBD228NLBM", _fetch_world_from_fred_lbma),
]


def get_world_spot_usd_per_oz():
    errors = []

    def fetch_source(source_info):
        source_name, source_url, fetcher = source_info
        try:
            price = to_float(fetcher())
            if _is_valid_world_price(price):
                return float(price), source_name, source_url
            raise ValueError(f"invalid price: {price}")
        except Exception as e:
            errors.append(f"{source_name}: {e}")
            raise

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(WORLD_SPOT_SOURCES)) as executor:
        future_to_source = {executor.submit(fetch_source, s): s[0] for s in WORLD_SPOT_SOURCES}
        for future in concurrent.futures.as_completed(future_to_source):
            try:
                result = future.result()
                if result:
                    print(f"World source success: {result[1]} -> {result[0]}")
                    return result
            except Exception:
                pass
    raise RuntimeError("All world sources failed: " + " | ".join(errors))


# ---------------------------------------------------------------------------
# Thai gold scrapers
# ---------------------------------------------------------------------------
def scrape_from_finnomena():
    print("Attempting Finnomena API...")
    url = "https://www.finnomena.com/fn-service/api/v2/gold/YLG"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.finnomena.com/gold"}
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()["data"]
    result = {
        "bar_buy": data["goldBar"]["bid"], "bar_sell": data["goldBar"]["ask"],
        "ornament_buy": data["ornament"]["bid"], "ornament_sell": data["ornament"]["ask"],
        "today_change": data["goldBar"]["change"], "date": data["updatedAt"].split("T")[0],
        "source_note": "Finnomena API",
    }
    print("Success from Finnomena API.")
    return normalize_prices(result)


def scrape_from_goldprice_or_th():
    print("Attempting goldprice.or.th API...")
    url = "https://www.goldprice.or.th/api/latest_price"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    r.raise_for_status()
    payload = r.json()

    def pick(row, keys):
        for key in keys:
            if isinstance(row, dict) and key in row and row.get(key) not in (None, ""):
                return row.get(key)
        return None

    candidate_rows = []
    if isinstance(payload, dict):
        if isinstance(payload.get("results"), list):
            candidate_rows.extend([x for x in payload["results"] if isinstance(x, dict)])
        if isinstance(payload.get("data"), list):
            candidate_rows.extend([x for x in payload["data"] if isinstance(x, dict)])
        if isinstance(payload.get("data"), dict):
            candidate_rows.append(payload["data"])
        if isinstance(payload.get("response"), dict):
            candidate_rows.append(payload["response"])
        candidate_rows.append(payload)
    elif isinstance(payload, list):
        candidate_rows.extend([x for x in payload if isinstance(x, dict)])

    for row in candidate_rows:
        data = {
            "bar_buy": pick(row, ("buy_bar", "bar_buy", "gold_bar_buy", "bid", "bid_bar")),
            "bar_sell": pick(row, ("sell_bar", "bar_sell", "gold_bar_sell", "ask", "ask_bar")),
            "ornament_buy": pick(row, ("buy_ornament", "ornament_buy", "jewelry_buy", "buy_jewelry")),
            "ornament_sell": pick(row, ("sell_ornament", "ornament_sell", "jewelry_sell", "sell_jewelry")),
            "today_change": pick(row, ("price_change", "today_change", "change")),
            "date": pick(row, ("date", "price_date", "updated_date")) or datetime.now().strftime("%Y-%m-%d"),
            "source_note": "goldprice.or.th API",
        }
        normalized = normalize_prices(data)
        if all(normalized.get(k) is not None for k in ("bar_buy", "bar_sell", "ornament_buy", "ornament_sell")):
            print("Success from goldprice.or.th API.")
            return normalized
    raise ValueError("goldprice.or.th payload format changed or incomplete")


def scrape_from_gta():
    print("Attempting goldtraders.or.th (HTML)...")
    r = requests.get("https://www.goldtraders.or.th/", timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    html = r.text

    def extract_val(pattern):
        match = re.search(pattern, html)
        if match:
            clean = re.sub(r"<[^>]+>", "", match.group(1)).replace(",", "").strip()
            return clean if clean else None
        return None

    bar_sell = extract_val(r'<span\s+id="DetailPlace_uc_goldprices1_lblBLSell"[^>]*>(.*?)</span>')
    bar_buy = extract_val(r'<span\s+id="DetailPlace_uc_goldprices1_lblBLBuy"[^>]*>(.*?)</span>')
    ornament_sell = extract_val(r'<span\s+id="DetailPlace_uc_goldprices1_lblOMSell"[^>]*>(.*?)</span>')
    ornament_buy = extract_val(r'<span\s+id="DetailPlace_uc_goldprices1_lblOMBuy"[^>]*>(.*?)</span>')
    today_change = extract_val(r'<span\s+id="DetailPlace_uc_goldprices1_lblDayChange"[^>]*>(.*?)</span>')
    update_text = extract_val(r'<span\s+id="DetailPlace_uc_goldprices1_lblDate"[^>]*>(.*?)</span>')

    if not (bar_sell and bar_buy and ornament_sell and ornament_buy):
        raise ValueError("Price values not found on GTA with regex.")

    update_round = ""
    if update_text:
        m = re.search(r"ครั้งที่\s*(\d+)", update_text)
        if m:
            update_round = m.group(1)
    if today_change:
        today_change = today_change.replace("+", "").strip()

    data = {
        "bar_buy": bar_buy, "bar_sell": bar_sell,
        "ornament_buy": ornament_buy, "ornament_sell": ornament_sell,
        "today_change": today_change or "0",
        "update_round": update_round or "ล่าสุด",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "source_note": "GTA (Regex)",
    }
    print(f"Success from GTA. Round: {update_round}, Change: {today_change}")
    return normalize_prices(data)


def scrape_from_thongkam():
    print("Attempting thongkam.com...")
    r = requests.get("https://xn--42cah7d0cxcvbbb9x.com/", timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    div = soup.find("div", id="divDaily")
    if not div:
        raise ValueError("divDaily not found")
    tds = div.select("td")
    data = {
        "bar_sell": tds[5].get_text(strip=True),
        "bar_buy": tds[6].get_text(strip=True),
        "ornament_sell": tds[9].get_text(strip=True),
        "ornament_buy": tds[10].get_text(strip=True),
        "source_note": "Thongkam.com",
    }
    try:
        page_text = soup.get_text()
        m = re.search(r"\(ครั้งที่\s*(\d+)\)", page_text)
        if m:
            data["update_round"] = m.group(1)
        cm = re.search(r"วันนี้(ขึ้น|ลง)(\d[\d,]*)", page_text)
        if cm:
            direction = cm.group(1)
            amount = cm.group(2).replace(",", "")
            data["today_change"] = int(amount) if direction == "ขึ้น" else -int(amount)
    except Exception as e:
        print(f"Could not extract round/change from thongkam: {e}")
    print(f"Success from thongkam.com.")
    return normalize_prices(data)


def scrape_from_intergold():
    print("Attempting intergold.co.th (AJAX)...")
    url = "https://www.intergold.co.th/wp-admin/admin-ajax.php"
    payload = {"action": "ajaxGetPriceApi", "type": "hour", "page": "1", "limit": "1"}
    r = requests.post(url, data=payload, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    body = r.json()
    html_rows = body.get("html")
    if not html_rows:
        raise ValueError("Intergold returned empty html payload")
    soup = BeautifulSoup(f"<table>{html_rows}</table>", "lxml")
    first_row = soup.find("tr")
    if not first_row:
        raise ValueError("Intergold returned no table row")
    cells = [td.get_text(strip=True) for td in first_row.find_all("td")]
    if len(cells) < 7:
        raise ValueError(f"Intergold row incomplete: {cells}")
    date_value = datetime.now().strftime("%Y-%m-%d")
    try:
        date_value = datetime.strptime(cells[0].split()[0], "%d/%m/%Y").strftime("%Y-%m-%d")
    except Exception:
        pass
    data = {
        "bar_buy": cells[5], "bar_sell": cells[6],
        "ornament_buy": cells[3], "ornament_sell": cells[4],
        "date": date_value, "source_note": "Intergold (AJAX)",
    }
    print(f"Success from intergold.co.th.")
    return normalize_prices(data)


def scrape_from_huasengheng():
    print("Attempting huasengheng.com API...")
    url = "https://www.huasengheng.com/wp-admin/admin-ajax.php"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.huasengheng.com/",
               "Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post(url, data={"action": "get_gold_price"}, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()
    if not data or not isinstance(data, dict):
        raise ValueError("Hua Seng Heng returned unexpected payload")
    price_data = {
        "bar_buy": data.get("buy965"),
        "bar_sell": data.get("sell965"),
        "ornament_buy": data.get("buy965_ornament", data.get("buy965")),
        "ornament_sell": data.get("sell965_ornament", data.get("sell965")),
        "today_change": data.get("change965"),
        "source_note": "HuaSengHeng (API)",
    }
    print("Success from Hua Seng Heng.")
    return normalize_prices(price_data)


def scrape_from_ecg():
    print("Attempting ecggoldshop.com...")
    r = requests.get("https://ecggoldshop.com/calculate/", timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    data = {
        "bar_buy": soup.find("input", {"id": "bar_buy"})["value"],
        "bar_sell": soup.find("input", {"id": "bar_sell"})["value"],
        "ornament_buy": soup.find("input", {"id": "jiw_sell"})["value"],
        "ornament_sell": soup.find("input", {"id": "jiw_buy"})["value"],
        "source_note": "ECG",
    }
    print("Success from ecggoldshop.com.")
    return normalize_prices(data)


# ---------------------------------------------------------------------------
# Cache refresh functions
# ---------------------------------------------------------------------------
def refresh_world_cache(force=False):
    now = time.time()
    if not force and world_cache.get("data") and now - world_cache.get("ts", 0) < CACHE_DURATION:
        return world_cache["data"]
    usd_per_oz, source_note, source_url = get_world_spot_usd_per_oz()
    usdthb = get_usdthb()
    thb_per_baht = usd_oz_to_thb_per_baht(usd_per_oz, usdthb)
    data = {
        "price_usd_per_ounce": round(usd_per_oz, 2),
        "usdthb": round(usdthb, 4),
        "thb_per_baht_est": round(thb_per_baht, 2),
        "last_updated": datetime.now().strftime("%H:%M:%S"),
        "source_note": source_note,
        "source_url": source_url,
    }
    world_cache.update({"data": data, "ts": now})
    return data


def refresh_thai_cache(force=False):
    now = time.time()
    prev_bar_sell = None
    if thai_cache.get("data") and thai_cache["data"].get("bar_sell") is not None:
        try:
            prev_bar_sell = float(thai_cache["data"]["bar_sell"])
        except Exception:
            pass

    if not force and thai_cache.get("data") and now - thai_cache.get("ts", 0) < CACHE_DURATION:
        return thai_cache["data"]

    scrapers = [
        scrape_from_gta, scrape_from_thongkam, scrape_from_goldprice_or_th,
        scrape_from_huasengheng, scrape_from_intergold, scrape_from_finnomena, scrape_from_ecg,
    ]

    def run_scraper(fn):
        data = fn()
        if not all(data.get(k) is not None for k in ("bar_buy", "bar_sell", "ornament_buy", "ornament_sell")):
            raise ValueError("Incomplete data")
        if not data.get("date"):
            data["date"] = datetime.now().strftime("%Y-%m-%d")
        if not data.get("update_round"):
            data["update_round"] = data.get("round") or "ล่าสุด"
        if data.get("today_change") is None:
            if prev_bar_sell is not None and data.get("bar_sell") is not None:
                data["today_change"] = float(data["bar_sell"]) - prev_bar_sell
            else:
                data["today_change"] = 0
        return data

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(scrapers)) as executor:
        future_to_fn = {executor.submit(run_scraper, fn): fn.__name__ for fn in scrapers}
        for future in concurrent.futures.as_completed(future_to_fn):
            try:
                data = future.result()
                thai_cache.update({"data": data, "ts": now})
                return data
            except Exception:
                pass

    if thai_cache.get("data"):
        stale = dict(thai_cache["data"])
        stale["stale"] = True
        return stale
    raise ValueError("All scrapers failed")
