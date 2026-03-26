"""services/notification.py — In-app, web-push, LINE notification helpers."""
import os
import json
import traceback

try:
    from pywebpush import webpush, WebPushException
    HAVE_WEBPUSH = True
except Exception:
    HAVE_WEBPUSH = False
    WebPushException = Exception


def _save_in_app_notification(conn, user_id, title, message, notif_type="price_alert", link="#alerts-container") -> bool:
    if not user_id:
        return False
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO notifications (user_id, title, message, type, link)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, title, message, notif_type, link),
            )
        return True
    except Exception as e:
        print(f"Failed to save in-app notification: {e}")
        return False


def _send_web_push(push_subscription, title: str, body: str, url: str = "#alerts-container") -> bool:
    if not HAVE_WEBPUSH:
        print("pywebpush not installed. Skip web push.")
        return False
    public_key = (os.getenv("VAPID_PUBLIC_KEY") or "").strip()
    private_key = (os.getenv("VAPID_PRIVATE_KEY") or "").strip()
    subject = (os.getenv("VAPID_SUBJECT") or "").strip()
    if not public_key or not private_key or not subject:
        print("VAPID config incomplete. Skip web push.")
        return False

    subscription = push_subscription
    if isinstance(subscription, str):
        try:
            subscription = json.loads(subscription)
        except Exception:
            print("Invalid push subscription JSON.")
            return False
    if not isinstance(subscription, dict) or not subscription.get("endpoint"):
        return False

    payload = json.dumps(
        {"title": title, "body": body, "url": url, "icon": "/img/logo.png", "badge": "/img/logo.png"},
        ensure_ascii=False,
    )
    try:
        webpush(
            subscription_info=subscription,
            data=payload,
            vapid_private_key=private_key,
            vapid_claims={"sub": subject},
            ttl=300,
        )
        return True
    except WebPushException as e:
        print(f"Web push failed: {e}")
        return False
    except Exception as e:
        print(f"Unexpected web push failure: {e}")
        return False


def _build_price_alert_message(alert, current_price):
    ptype = alert.get("gold_type", "bar")
    atype = alert.get("alert_type", "above")
    target_price = float(alert.get("target_price") or 0)
    user_name = alert.get("name") or "ลูกค้า"
    type_map = {"bar": "ทองคำแท่ง", "ornament": "ทองรูปพรรณ", "world": "ทองโลก (USD/oz)"}
    type_text = type_map.get(ptype, ptype)
    condition_text = "สูงกว่า หรือ เท่ากับ" if atype == "above" else "ต่ำกว่า หรือ เท่ากับ"
    is_world = ptype == "world"
    money_prefix = "$" if is_world else "฿"
    current_text = f"{float(current_price or 0):,.2f}"
    target_text = f"{target_price:,.2f}"
    title = f"🔔 แจ้งเตือนราคาทอง: {type_text}"
    body = f"{type_text} {condition_text} {money_prefix}{target_text} แล้ว (ตอนนี้ {money_prefix}{current_text})"
    line_text = (
        f"🔔 แจ้งเตือนราคาทอง\n"
        f"- ผู้ใช้: {user_name}\n"
        f"- ประเภท: {type_text}\n"
        f"- เงื่อนไข: {condition_text} {money_prefix}{target_text}\n"
        f"- ราคาปัจจุบัน: {money_prefix}{current_text}"
    )
    return {"title": title, "body": body, "line_text": line_text}


def _deliver_price_alert(conn, alert, current_price, stats=None):
    from services.line_service import _line_push
    from services.email_service import send_alert_email_smtp

    stats = stats if isinstance(stats, dict) else None
    delivery = {"notified": False, "line_sent": False, "push_sent": False, "email_sent": False, "in_app_saved": False}

    message = _build_price_alert_message(alert, current_price)
    delivery["in_app_saved"] = _save_in_app_notification(
        conn, alert.get("user_id"), message["title"], message["body"],
        notif_type="price_alert", link="#alerts-container",
    )
    if stats is not None and delivery["in_app_saved"]:
        stats["notifications_saved"] = stats.get("notifications_saved", 0) + 1

    line_user_id = (alert.get("line_user_id") or "").strip()
    if line_user_id:
        delivery["line_sent"] = _line_push(line_user_id, message["line_text"])
        if stats is not None and delivery["line_sent"]:
            stats["line_sent"] = stats.get("line_sent", 0) + 1

    if not delivery["line_sent"] and alert.get("push_subscription"):
        delivery["push_sent"] = _send_web_push(
            alert.get("push_subscription"), message["title"], message["body"], url="#alerts-container",
        )
        if stats is not None and delivery["push_sent"]:
            stats["push_sent"] = stats.get("push_sent", 0) + 1

    if not delivery["line_sent"] and not delivery["push_sent"]:
        delivery["email_sent"] = send_alert_email_smtp(alert, current_price)
        if stats is not None and delivery["email_sent"]:
            stats["email_sent"] = stats.get("email_sent", 0) + 1

    delivery["notified"] = delivery["line_sent"] or delivery["push_sent"] or delivery["email_sent"]
    return delivery
