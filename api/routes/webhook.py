"""routes/webhook.py — LINE webhook endpoint."""
import re
import traceback
from flask import Blueprint, jsonify, request
from database.connection import get_db_connection, _ensure_users_columns
from services.line_service import (
    _line_signature_ok, _line_reply, _line_menu_text, _line_get_cached_prices_text,
    _line_status_text, _line_unlink, _line_get_display_name,
)

webhook_bp = Blueprint("webhook", __name__)


@webhook_bp.route("/webhook", methods=["POST", "GET"])
def line_webhook():
    if request.method == "GET":
        return "OK", 200

    body = request.get_data() or b""
    signature = request.headers.get("X-Line-Signature", "")
    if not _line_signature_ok(body, signature):
        return "Invalid signature", 400

    payload = request.get_json(silent=True) or {}
    events = payload.get("events") or []

    for event in events:
        try:
            if (event or {}).get("type") != "message":
                continue
            msg = (event.get("message") or {})
            if msg.get("type") != "text":
                continue
            reply_token = event.get("replyToken")
            text = (msg.get("text") or "").strip()
            source = event.get("source") or {}
            line_user_id = source.get("userId")
            if not reply_token:
                continue

            print(f"LINE inbound: {text}")
            t = text.lower()

            if t in ("help", "menu", "ช่วยเหลือ", "เมนู", "?"):
                _line_reply(reply_token, _line_menu_text())
                continue

            if t in ("price", "ราคา", "ราคาทอง", "ทอง", "gold"):
                price_text = _line_get_cached_prices_text("all")
                _line_reply(reply_token, price_text or "ตอนนี้ยังไม่มีข้อมูลราคาในระบบ cache\nลองเปิดหน้าเว็บสักครู่ แล้วพิมพ์ \"ราคา\" อีกครั้งครับ")
                continue

            if t in ("ราคาทองโลก", "ทองโลก", "world", "world gold", "xauusd"):
                world_text = _line_get_cached_prices_text("world")
                _line_reply(reply_token, world_text or "ตอนนี้ยังไม่มีข้อมูลราคาทองโลกในระบบ cache\nลองใหม่อีกครั้งในอีกสักครู่ครับ")
                continue

            if t in ("status", "สถานะ", "unlink", "ยกเลิก", "เลิก", "disconnect") or re.match(r"^(?:LINK-)?(\d{6})$", text, flags=re.IGNORECASE):
                try:
                    conn = get_db_connection()
                except Exception:
                    traceback.print_exc()
                    _line_reply(reply_token, "ระบบฐานข้อมูลมีปัญหาชั่วคราว ลองใหม่อีกครั้งครับ")
                    continue

                try:
                    _ensure_users_columns(conn, ("verification_token", "line_user_id", "line_display_name"))
                    if t in ("status", "สถานะ"):
                        _line_reply(reply_token, _line_status_text(conn, line_user_id))
                        continue
                    if t in ("unlink", "ยกเลิก", "เลิก", "disconnect"):
                        ok = _line_unlink(conn, line_user_id)
                        conn.commit()
                        _line_reply(reply_token, "✅ ยกเลิกการเชื่อมต่อเรียบร้อยแล้ว" if ok else "ไม่พบการเชื่อมต่อที่ต้องยกเลิก")
                        continue
                    m = re.match(r"^(?:LINK-)?(\d{6})$", text, flags=re.IGNORECASE)
                    if not m:
                        _line_reply(reply_token, "พิมพ์ \"ช่วยเหลือ\" เพื่อดูเมนูคำสั่ง")
                        continue
                    code = m.group(1)
                    display_name = _line_get_display_name(line_user_id) if line_user_id else None
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT id, name FROM users WHERE verification_token=%s AND is_active=1 LIMIT 1", (code,))
                        user = cursor.fetchone()
                        if not user:
                            _line_reply(reply_token, "❌ รหัสเชื่อมต่อไม่ถูกต้อง หรือหมดอายุแล้วครับ")
                            continue
                        cursor.execute(
                            "UPDATE users SET line_user_id=%s, line_display_name=%s, verification_token=NULL WHERE id=%s",
                            (line_user_id, display_name, user["id"]),
                        )
                    conn.commit()
                    name = user.get("name") or "ผู้ใช้"
                    _line_reply(reply_token, f"✅ เชื่อมต่อสำเร็จ! สวัสดีคุณ {name}\nต่อไปนี้คุณจะได้รับแจ้งเตือนราคาทองผ่าน LINE นี้ครับ")
                    continue
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass

            _line_reply(reply_token, "พิมพ์ \"ช่วยเหลือ\" เพื่อดูเมนูคำสั่ง\nหรือส่งรหัสเชื่อมต่อจากหน้าเว็บไซต์ในรูปแบบ LINK-123456 เพื่อเชื่อมบัญชีครับ")
        except Exception:
            traceback.print_exc()

    return "OK", 200
