"""routes/prices.py — Thai gold, world gold, intraday, historical endpoints."""
import time
import traceback
import threading
from datetime import datetime

from flask import Blueprint, jsonify, request

from services.gold_price import refresh_thai_cache, refresh_world_cache, thai_cache, world_cache
from services.historical import (
    historical_cache, intraday_cache, HAVE_YFINANCE,
    build_series_with_world_from_yfinance, build_historical_gold_data_free,
    _build_intraday_fallback_payload,
)
from services.scheduler import save_daily_price
from utils.helpers import to_float, get_usdthb

try:
    import yfinance as yf
except ImportError:
    yf = None

CACHE_DURATION = 30
prices_bp = Blueprint("prices", __name__)


@prices_bp.route("/api/world-gold-price")
def api_world():
    try:
        data = refresh_world_cache()
        return jsonify(data)
    except Exception as e:
        print(f"WORLD PRICE ERROR: {e}"); traceback.print_exc()
        if world_cache.get("data"):
            stale = dict(world_cache["data"])
            stale["stale"] = True
            return jsonify(stale), 200
        try:
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
                return jsonify(data), 200
        except Exception:
            pass
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
        return jsonify(data), 200


@prices_bp.route("/api/thai-gold-price")
def api_thai():
    try:
        data = refresh_thai_cache()
        try:
            threading.Thread(target=save_daily_price, daemon=True).start()
        except Exception:
            pass
        return jsonify(data)
    except Exception as e:
        print(f"FATAL ERROR in api_thai: {e}"); traceback.print_exc()
        return jsonify({"error": "Internal Server Error in Thai Price API"}), 500


@prices_bp.route("/api/historical")
def api_historical():
    try:
        days = int(request.args.get("days", 365))
        days = max(30, min(days, 365))
        now = time.time()
        today = datetime.now().date().isoformat()
        if (historical_cache["data"] and historical_cache.get("date") == today
                and now - historical_cache["ts"] < CACHE_DURATION):
            return jsonify(historical_cache["data"])
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
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "ไม่สามารถโหลดข้อมูลย้อนหลังได้", "details": str(e)}), 500


@prices_bp.route("/api/intraday")
def api_intraday():
    try:
        now = time.time()
        time_range = request.args.get("range", "1d").lower()
        range_config = {"1d": "5m", "5d": "15m", "1w": "1h", "1mo": "1d"}
        if time_range not in range_config:
            time_range = "1d"
        interval = range_config[time_range]
        cache_key = f"intraday_{time_range}"
        if cache_key in intraday_cache and now - intraday_cache[cache_key]["ts"] < 120:
            return jsonify(intraday_cache[cache_key]["data"])

        labels, thai_values, world_values, assoc_values, source = [], [], [], [], ""
        if HAVE_YFINANCE and yf:
            try:
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
                    try:
                        real_bar_sell = None
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
            return jsonify(data)

        if assoc_values and thai_cache["data"] and thai_cache["data"].get("bar_sell"):
            assoc_values[-1] = float(thai_cache["data"]["bar_sell"])

        data = {
            "labels": labels, "thai_values": thai_values, "world_values": world_values,
            "assoc_values": assoc_values, "source": source,
            "updated_at": datetime.now().isoformat(),
        }
        intraday_cache[cache_key] = {"data": data, "ts": now}
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        safe_range = request.args.get("range", "1d").lower()
        data = _build_intraday_fallback_payload(safe_range, "Emergency Fallback")
        data["warning"] = str(e)
        key = f"intraday_{safe_range if safe_range in ('1d', '5d', '1w', '1mo') else '1d'}"
        intraday_cache[key] = {"data": data, "ts": time.time()}
        return jsonify(data), 200


@prices_bp.route("/api/news")
def api_news():
    import requests
    import xml.etree.ElementTree as ET
    from datetime import datetime
    import urllib.parse
    
    # 1. รับคำค้นหา ดึงค่าเริ่มต้นเป็น "ราคาทอง"
    query = request.args.get("q", "ราคาทอง")
    if query.lower() == "gold":
        # ถ้า frontend ขอ gold เปลี่ยนเป็นภาษาไทยเพื่อให้เหมาะกับผู้ใช้คนไทย
        query = "ราคาทอง"
        
    encoded_query = urllib.parse.quote(query)
    
    # 2. ใช้ Google News RSS แบบรองรับภาษาไทย
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=th&gl=TH&ceid=TH:th"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        resp = requests.get(rss_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            raise Exception(f"Google News RSS returned status {resp.status_code}")
            
        root = ET.fromstring(resp.text)
        articles = []
        
        import re
        
        # รูปภาพสุ่มสำหรับข่าวทองคำเนื่องจาก Google RSS ไม่มีรูปมาให้
        fallback_images = [
            "https://images.unsplash.com/photo-1610375461246-83df859d849d?w=600&q=80",
            "https://images.unsplash.com/photo-1599387819932-b883088b9dd6?w=600&q=80",
            "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=600&q=80",
            "https://images.unsplash.com/photo-1610375461320-b420f1ec3795?w=600&q=80",
            "https://images.unsplash.com/photo-1610052204791-c67299a9a5f7?w=600&q=80",
            "https://images.unsplash.com/photo-1633158829585-23ba8f7c8caf?w=600&q=80",
            "https://images.unsplash.com/photo-1579621970588-a35d0e7ab9b6?w=600&q=80",
        ]
        
        # 3. แปลง XML เป็นโครงสร้างเดียวกับที่ frontend (NewsAPI format) รองรับ
        for i, item in enumerate(root.findall('.//item')[:10]):  # ดึงมา 10 ข่าวล่าสุด
            title = item.find('title')
            link = item.find('link')
            pub_date = item.find('pubDate')
            source = item.find('source')
            desc = item.find('description')
            
            # ลบชื่อสำนักข่าวออกจากท้าย title ถ้ายาวเกินไป
            title_text = (title.text or "").strip()
            if " - " in title_text:
                title_text = " - ".join(title_text.split(" - ")[:-1])
                
            # ตัดช่องว่างบรรทัดใหม่จาก URL (สาเหตุหลักที่ทำให้ลิงก์ไปหน้า about:blank)
            url_text = (link.text or "#").strip()
            
            # ดึงข้อความเพียวๆ จาก description ที่เป็น HTML
            desc_text = ""
            if desc is not None and desc.text:
                desc_text = re.sub('<[^<]+>', '', desc.text).strip()
                # ตัดข้อความให้สั้นลง
                if len(desc_text) > 120:
                    desc_text = desc_text[:117] + "..."
                
            articles.append({
                "title": title_text,
                "url": url_text,
                "urlToImage": fallback_images[i % len(fallback_images)],
                "publishedAt": (pub_date.text or datetime.now().isoformat()).strip(),
                "source": {
                    "name": (source.text or "Google News").strip()
                },
                "description": desc_text
            })
            
        return jsonify({
            "status": "ok",
            "totalResults": len(articles),
            "articles": articles
        }), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Fallback to Mock Data if error
        mock_news = {
            "status": "ok",
            "articles": [
                {
                    "title": "[Demo] ราคาทองวันนี้ สมาคมค้าทองคำประกาศ...",
                    "description": "เกิดข้อผิดพลาดในการดึงข้อมูลจากดึงจากข่าว (นี่คือข้อมูลจำลอง)",
                    "url": "#",
                    "source": {"name": "ระบบข่าวสำรอง"},
                    "publishedAt": datetime.now().isoformat()
                }
            ]
        }
        return jsonify(mock_news), 200
