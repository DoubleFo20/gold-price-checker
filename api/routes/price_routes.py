# routes/price_routes.py – Routes for price‑related endpoints
"""All price‑related API endpoints are defined here and delegated to
service layer functions. This module registers a Flask Blueprint named
``price_bp`` which is imported by ``server.py``.
"""

from flask import Blueprint, jsonify, request

# Service wrappers
from services.gold_price_service import get_world_price, get_thai_price
from services.historical_service import get_intraday

price_bp = Blueprint("price", __name__)

# -------------------- World Gold Price --------------------
@price_bp.route("/api/world-gold-price")
def world_gold_price():
    data = get_world_price()
    return jsonify(data)

# -------------------- Thai Gold Price --------------------
@price_bp.route("/api/thai-gold-price")
def thai_gold_price():
    data = get_thai_price()
    if "error" in data:
        return jsonify(data), 500
    return jsonify(data)

# -------------------- Intraday --------------------
@price_bp.route("/api/intraday")
def intraday():
    time_range = request.args.get("range", "1d").lower()
    data = get_intraday(time_range)
    return jsonify(data)

# -------------------- News (unchanged) --------------------
@price_bp.route("/api/news")
def news():
    import requests
    import xml.etree.ElementTree as ET
    from datetime import datetime
    import urllib.parse
    import re

    query = request.args.get("q", "ราคาทอง")
    if query.lower() == "gold":
        query = "ราคาทอง"
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=th&gl=TH&ceid=TH:th"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        resp = requests.get(rss_url, headers=headers, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        articles = []
        fallback_images = [
            "https://images.unsplash.com/photo-1610375461246-83df859d849d?w=600&q=80",
            "https://images.unsplash.com/photo-1599387819932-b883088b9dd6?w=600&q=80",
            "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=600&q=80",
            "https://images.unsplash.com/photo-1610375461320-b420f1ec3795?w=600&q=80",
            "https://images.unsplash.com/photo-1610052204791-c67299a9a5f7?w=600&q=80",
            "https://images.unsplash.com/photo-1633158829585-23ba8f7c8caf?w=600&q=80",
            "https://images.unsplash.com/photo-1579621970588-a35d0e7ab9b6?w=600&q=80",
        ]
        for i, item in enumerate(root.findall('.//item')[:10]):
            title = item.find('title')
            link = item.find('link')
            pub_date = item.find('pubDate')
            source = item.find('source')
            desc = item.find('description')
            title_text = (title.text or "").strip()
            if " - " in title_text:
                title_text = " - ".join(title_text.split(" - ")[:-1])
            url_text = (link.text or "#").strip()
            desc_text = ""
            if desc is not None and desc.text:
                desc_text = re.sub('<[^<]+>', '', desc.text).strip()
                if len(desc_text) > 120:
                    desc_text = desc_text[:117] + "..."
            articles.append({
                "title": title_text,
                "url": url_text,
                "urlToImage": fallback_images[i % len(fallback_images)],
                "publishedAt": (pub_date.text or datetime.now().isoformat()).strip(),
                "source": {"name": (source.text or "Google News").strip()},
                "description": desc_text,
            })
        return jsonify({"status": "ok", "totalResults": len(articles), "articles": articles}), 200
    except Exception as e:
        mock_news = {
            "status": "ok",
            "articles": [
                {
                    "title": "[Demo] ราคาทองวันนี้ สมาคมค้าทองคำประกาศ...",
                    "description": "เกิดข้อผิดพลาดในการดึงข้อมูลจากดึงจากข่าว (นี่คือข้อมูลจำลอง)",
                    "url": "#",
                    "source": {"name": "ระบบข่าวสำรอง"},
                    "publishedAt": datetime.now().isoformat(),
                }
            ],
        }
        return jsonify(mock_news), 200
