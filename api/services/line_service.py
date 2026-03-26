"""services/line_service.py — LINE Messaging API helpers."""
import os
import re
import hmac
import hashlib
import base64
import traceback
import requests


def _line_connect_meta():
    bot_id = (os.getenv("LINE_BOT_ID") or "").strip()
    add_friend_url = (os.getenv("LINE_ADD_FRIEND_URL") or "").strip()
    if (not add_friend_url) and bot_id:
        normalized = bot_id if bot_id.startswith("@") else f"@{bot_id}"
        add_friend_url = f"https://line.me/R/ti/p/{normalized}"
    return {"line_bot_id": bot_id, "add_friend_url": add_friend_url}


def _line_push(line_user_id: str, text: str) -> bool:
    token = (os.getenv("LINE_CHANNEL_ACCESS_TOKEN") or "").strip()
    if not token or not line_user_id:
        return False
    try:
        r = requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            json={"to": line_user_id, "messages": [{"type": "text", "text": text}]},
            timeout=10,
        )
        if not r.ok:
            print(f"LINE push failed: {r.status_code} {r.text[:200]}")
        return bool(r.ok)
    except Exception:
        traceback.print_exc()
        return False


def _line_reply(reply_token: str, text: str) -> None:
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not token or not reply_token:
        return
    try:
        r = requests.post(
            "https://api.line.me/v2/bot/message/reply",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            json={"replyToken": reply_token, "messages": [{"type": "text", "text": text}]},
            timeout=10,
        )
        if not r.ok:
            print(f"LINE reply failed: {r.status_code} {r.text[:200]}")
    except Exception:
        traceback.print_exc()


def _line_get_display_name(line_user_id: str):
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not token or not line_user_id:
        return None
    try:
        r = requests.get(
            f"https://api.line.me/v2/bot/profile/{line_user_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if r.ok:
            return (r.json() or {}).get("displayName")
    except Exception:
        traceback.print_exc()
    return None


def _line_menu_text() -> str:
    return (
        "เมนูคำสั่ง (พิมพ์ได้เลย)\n"
        "- ราคา : ดูราคาล่าสุดทั้งหมด\n"
        "- ราคาทองโลก : ดูราคาทองโลก (XAUUSD)\n"
        "- สถานะ : ดูว่าเชื่อมบัญชีแล้วหรือยัง\n"
        "- LINK-123456 หรือ 123456 : เชื่อมบัญชี (ใช้รหัสจากหน้าเว็บ)\n"
        "- ยกเลิก : ยกเลิกการเชื่อมต่อ LINE\n"
        "- ช่วยเหลือ : ดูเมนูนี้อีกครั้ง"
    )


def _line_get_cached_prices_text(price_mode: str = "all"):
    from services.gold_price import thai_cache, world_cache
    try:
        thai = thai_cache.get("data") or {}
        world = world_cache.get("data") or {}
        have_thai = all(thai.get(k) is not None for k in ("bar_buy", "bar_sell", "ornament_buy", "ornament_sell"))
        have_world = world.get("price_usd_per_ounce") is not None
        if not have_thai and not have_world:
            return None
        parts = []
        mode = (price_mode or "all").lower()
        include_thai = mode in ("all", "thai")
        include_world = mode in ("all", "world")
        if include_thai and have_thai:
            parts.append("ราคาทองไทย (ล่าสุด)")
            parts.append(f"- ทองคำแท่ง รับซื้อ: ฿{float(thai['bar_buy']):,.2f} | ขายออก: ฿{float(thai['bar_sell']):,.2f}")
            parts.append(f"- ทองรูปพรรณ รับซื้อ: ฿{float(thai['ornament_buy']):,.2f} | ขายออก: ฿{float(thai['ornament_sell']):,.2f}")
        if include_world and have_world:
            parts.append(f"ทองโลก (XAUUSD): ${float(world['price_usd_per_ounce']):,.2f}/oz")
        if include_thai and (thai.get("date") or thai.get("update_round")):
            parts.append(f"อัปเดต: {thai.get('date', '')} {thai.get('update_round', '')}".strip())
        return "\n".join(parts)
    except Exception:
        traceback.print_exc()
        return None


def _line_signature_ok(body: bytes, signature: str) -> bool:
    secret = os.getenv("LINE_CHANNEL_SECRET", "")
    if not secret or not signature:
        return True
    mac = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def _line_unlink(conn, line_user_id: str) -> bool:
    from database.connection import _ensure_users_columns
    if not line_user_id:
        return False
    _ensure_users_columns(conn, ("line_user_id", "line_display_name"))
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE users SET line_user_id=NULL, line_display_name=NULL WHERE line_user_id=%s",
            (line_user_id,),
        )
        return cursor.rowcount > 0


def _line_status_text(conn, line_user_id: str) -> str:
    from database.connection import _ensure_users_columns
    if not line_user_id:
        return "ไม่พบ LINE userId"
    _ensure_users_columns(conn, ("line_user_id",))
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT id, name FROM users WHERE line_user_id=%s AND is_active=1 LIMIT 1",
            (line_user_id,),
        )
        user = cursor.fetchone()
    if user:
        name = user.get("name") or "ผู้ใช้"
        return f"✅ เชื่อมต่อแล้วกับบัญชี: {name}"
    return "ยังไม่ได้เชื่อมต่อบัญชีครับ\nพิมพ์ LINK-123456 หรือ 123456 (รับรหัสจากหน้าเว็บ) เพื่อเชื่อมบัญชี"
