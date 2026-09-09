"""services/email_service.py — SMTP email senders and delivery tracking."""
import html
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _smtp_config():
    return {
        "host": os.getenv("SMTP_HOST", "").strip(),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": os.getenv("SMTP_USER", "").strip(),
        "password": os.getenv("SMTP_PASS", "").strip(),
        "from_email": (os.getenv("SMTP_FROM_EMAIL", "") or os.getenv("SMTP_USER", "")).strip(),
        "from_name": os.getenv("SMTP_FROM_NAME", "Gold Price Today").strip(),
    }


def _app_base_url():
    url = (os.getenv("APP_URL") or os.getenv("SITE_URL") or "http://localhost:5000").strip()
    return url.rstrip("/")


def log_email_attempt(to_email: str, subject: str, status: str, error_message: str = None, user_id: int = None) -> bool:
    """Record outbound email attempt (success or failure) in email_logs table."""
    try:
        from database.connection import get_db_connection
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(
                        """
                        INSERT INTO email_logs (user_id, recipient_email, subject, status, error_message, sent_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        """,
                        (user_id, to_email or "", subject or "", status, error_message),
                    )
                except Exception:
                    cursor.execute(
                        """
                        INSERT INTO email_logs (user_id, recipient, subject, status, error_message, sent_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        """,
                        (user_id, to_email or "", subject or "", status, error_message),
                    )
            conn.commit()
            return True
        finally:
            conn.close()
    except Exception as e:
        print(f"Failed to record email log: {e}")
        return False


def _send_smtp(cfg, to_email, subject, text_body, html_body, user_id=None) -> bool:
    if not to_email:
        print("No recipient email.")
        log_email_attempt(to_email or "", subject, "failed", "No recipient email", user_id=user_id)
        return False
    if not cfg.get("host") or not cfg.get("user") or not cfg.get("password") or not cfg.get("from_email"):
        print("SMTP config incomplete. Skipping.")
        log_email_attempt(to_email, subject, "failed", "SMTP config incomplete", user_id=user_id)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{cfg['from_name']} <{cfg['from_email']}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=20) as server:
            server.ehlo()
            if cfg["port"] == 587:
                server.starttls()
                server.ehlo()
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["from_email"], [to_email], msg.as_string())
        log_email_attempt(to_email, subject, "sent", None, user_id=user_id)
        return True
    except Exception as e:
        print(f"SMTP send failed to {to_email}: {e}")
        log_email_attempt(to_email, subject, "failed", str(e), user_id=user_id)
        return False


def send_alert_email_smtp(alert, current_price) -> bool:
    cfg = _smtp_config()
    to_email = (alert.get("receiver_email") or alert.get("notify_email") or alert.get("email") or "").strip()
    ptype = alert.get("gold_type", "bar")
    atype = alert.get("alert_type", "above")
    target_price = float(alert.get("target_price") or 0)
    user_name = html.escape(str(alert.get("name") or "ลูกค้า").strip())
    user_id = alert.get("user_id")
    type_map = {"bar": "ทองคำแท่ง", "ornament": "ทองรูปพรรณ", "world": "ทองโลก (USD/oz)"}
    type_text = type_map.get(ptype, ptype)
    condition_text = "สูงกว่า หรือ เท่ากับ" if atype == "above" else "ต่ำกว่า หรือ เท่ากับ"
    money_prefix = "$" if ptype == "world" else "฿"
    current_text = f"{current_price:,.2f}"
    target_text = f"{target_price:,.2f}"
    subject = f"🔔 แจ้งเตือนราคาทอง: {type_text}"

    html_body = f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>แจ้งเตือนราคาทองคำ</title>
  </head>
  <body style="font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background-color:#f4f6f9;margin:0;padding:20px;color:#333;">
    <div style="max-width:600px;margin:0 auto;background:#fff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,0.08);">
      <div style="background:linear-gradient(135deg,#d4af37,#b8860b);color:#fff;padding:24px 30px;text-align:center;">
        <h2 style="margin:0;font-size:22px;font-weight:700;letter-spacing:0.5px;">🔔 ระบบแจ้งเตือนราคาทองคำ</h2>
        <p style="margin:6px 0 0 0;font-size:14px;opacity:0.9;">Gold Price Today</p>
      </div>
      <div style="padding:26px 30px;color:#333;">
        <p style="font-size:16px;margin-top:0;">สวัสดีคุณ <strong>{user_name}</strong>,</p>
        <p style="font-size:15px;line-height:1.6;color:#4a5568;">{type_text} ถึงเงื่อนไข <strong>{condition_text}</strong> ที่คุณตั้งไว้เรียบร้อยแล้ว</p>
        <div style="background:#f7fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px 20px;margin:20px 0;">
          <p style="margin:6px 0;font-size:15px;"><strong>ราคาปัจจุบัน:</strong> <span style="color:#b8860b;font-weight:bold;font-size:17px;">{money_prefix}{current_text}</span></p>
          <p style="margin:6px 0;font-size:15px;"><strong>ราคาเป้าหมาย:</strong> <span style="color:#2d3748;font-weight:bold;">{money_prefix}{target_text}</span></p>
        </div>
        <p style="font-size:13px;color:#718096;margin-top:20px;">เปิดดูรายละเอียดและกราฟวิเคราะห์แนวโน้มได้ที่ระบบ Gold Price Today</p>
      </div>
      <div style="background:#fafafa;padding:16px 30px;text-align:center;font-size:12px;color:#a0aec0;border-top:1px solid #edf2f7;">
        &copy; Gold Price Today. All rights reserved.
      </div>
    </div>
  </body>
</html>"""
    text_body = (
        f"แจ้งเตือนราคาทอง | Gold Price Today\n\n"
        f"สวัสดีคุณ {user_name},\n"
        f"ประเภท: {type_text}\n"
        f"เงื่อนไข: {condition_text}\n"
        f"ราคาปัจจุบัน: {money_prefix}{current_text}\n"
        f"ราคาเป้าหมาย: {money_prefix}{target_text}\n"
    )
    return _send_smtp(cfg, to_email, subject, text_body, html_body, user_id=user_id)


def send_forecast_email_smtp(payload) -> bool:
    cfg = _smtp_config()
    to_email = (payload.get("email") or "").strip()
    user_name = html.escape(str(payload.get("name") or "ลูกค้า").strip())
    user_id = payload.get("user_id")
    target_date_raw = str(payload.get("target_date") or "").strip()
    trend = html.escape(str(payload.get("trend") or "-"))
    max_price = float(payload.get("max_price") or 0)
    min_price = float(payload.get("min_price") or 0)
    confidence = float(payload.get("confidence") or 0)
    hist_days = int(payload.get("hist_days") or 0)

    target_date_display = target_date_raw
    try:
        d = datetime.fromisoformat(target_date_raw[:10])
        target_date_display = f"{d.day}/{d.month}/{d.year + 543}"
    except Exception:
        pass

    subject = f"📈 สรุปพยากรณ์ราคาทอง | วันที่เป้าหมาย {target_date_display}"
    html_body = f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>บันทึกพยากรณ์ราคาทองคำ</title>
  </head>
  <body style="font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background-color:#f4f6f9;margin:0;padding:20px;color:#333;">
    <div style="max-width:600px;margin:0 auto;background:#fff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,0.08);">
      <div style="background:linear-gradient(135deg,#d4af37,#b8860b);color:#fff;padding:24px 30px;text-align:center;">
        <h2 style="margin:0;font-size:22px;font-weight:700;letter-spacing:0.5px;">📈 บันทึกพยากรณ์ราคาทองคำสำเร็จ</h2>
        <p style="margin:6px 0 0 0;font-size:14px;opacity:0.9;">Gold Price Today</p>
      </div>
      <div style="padding:26px 30px;color:#333;">
        <p style="font-size:16px;margin-top:0;">สวัสดีคุณ <strong>{user_name}</strong>,</p>
        <div style="background:#f7fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px 20px;margin:20px 0;">
          <p style="margin:6px 0;font-size:15px;"><strong>พยากรณ์สำหรับวันที่:</strong> {target_date_display}</p>
          <p style="margin:6px 0;font-size:15px;"><strong>แนวโน้ม:</strong> {trend}</p>
          <p style="margin:6px 0;font-size:15px;"><strong>ราคามากสุด (พยากรณ์):</strong> ฿{max_price:,.2f}</p>
          <p style="margin:6px 0;font-size:15px;"><strong>ราคาน้อยสุด (พยากรณ์):</strong> ฿{min_price:,.2f}</p>
          <p style="margin:6px 0;font-size:15px;"><strong>ความเชื่อมั่น (R²):</strong> {confidence:.2f}%</p>
          <p style="margin:6px 0;font-size:15px;"><strong>ข้อมูลย้อนหลังที่ใช้:</strong> {hist_days} วัน</p>
        </div>
      </div>
      <div style="background:#fafafa;padding:16px 30px;text-align:center;font-size:12px;color:#a0aec0;border-top:1px solid #edf2f7;">
        &copy; Gold Price Today. All rights reserved.
      </div>
    </div>
  </body>
</html>"""
    text_body = (
        f"บันทึกพยากรณ์ราคาทองคำสำเร็จ\n"
        f"พยากรณ์สำหรับวันที่: {target_date_display}\n"
        f"แนวโน้ม: {trend}\n"
        f"ราคามากสุด: ฿{max_price:,.2f}\n"
        f"ราคาน้อยสุด: ฿{min_price:,.2f}\n"
        f"ความเชื่อมั่น: {confidence:.2f}%\n"
        f"ข้อมูลย้อนหลังที่ใช้: {hist_days} วัน\n"
    )
    return _send_smtp(cfg, to_email, subject, text_body, html_body, user_id=user_id)


def send_forecast_result_email_smtp(payload) -> bool:
    cfg = _smtp_config()
    to_email = (payload.get("email") or "").strip()
    user_name = html.escape(str(payload.get("name") or "ลูกค้า").strip())
    user_id = payload.get("user_id")
    target_date_display = payload.get("target_date_display") or "-"
    pred_min = float(payload.get("pred_min") or 0)
    pred_max = float(payload.get("pred_max") or 0)
    actual_buy = float(payload.get("actual_buy") or 0)
    actual_sell = float(payload.get("actual_sell") or 0)
    is_accurate = bool(payload.get("is_accurate"))
    status_text = "แม่นยำ ✅" if is_accurate else "ไม่แม่นยำ ❌"
    status_color = "#16A085" if is_accurate else "#e74c3c"

    subject = f"📊 ผลจริงพยากรณ์ทองคำ ({target_date_display}) {status_text}"
    html_body = f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ผลจริงพยากรณ์ทองคำ</title>
  </head>
  <body style="font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background-color:#f4f6f9;margin:0;padding:20px;color:#333;">
    <div style="max-width:600px;margin:0 auto;background:#fff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,0.08);">
      <div style="background:linear-gradient(135deg,#d4af37,#b8860b);color:#fff;padding:24px 30px;text-align:center;">
        <h2 style="margin:0;font-size:22px;font-weight:700;letter-spacing:0.5px;">📊 อัปเดตผลพยากรณ์ถึงวันเป้าหมายแล้ว</h2>
        <p style="margin:6px 0 0 0;font-size:14px;opacity:0.9;">Gold Price Today</p>
      </div>
      <div style="padding:26px 30px;color:#333;">
        <p style="font-size:16px;margin-top:0;">สวัสดีคุณ <strong>{user_name}</strong>,</p>
        <div style="background:#f7fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px 20px;margin:20px 0;">
          <p style="margin:6px 0;font-size:15px;"><strong>พยากรณ์สำหรับวันที่:</strong> {target_date_display}</p>
          <p style="margin:6px 0;font-size:15px;"><strong>ผลการประเมิน:</strong> <span style="color:{status_color};font-weight:bold;">{status_text}</span></p>
          <p style="margin:6px 0;font-size:15px;"><strong>ช่วงพยากรณ์:</strong> ฿{pred_min:,.2f} - ฿{pred_max:,.2f}</p>
          <p style="margin:6px 0;font-size:15px;"><strong>ราคาจริง (ขายออก):</strong> ฿{actual_sell:,.2f}</p>
          <p style="margin:6px 0;font-size:15px;"><strong>ราคาจริง (รับซื้อ):</strong> ฿{actual_buy:,.2f}</p>
        </div>
      </div>
      <div style="background:#fafafa;padding:16px 30px;text-align:center;font-size:12px;color:#a0aec0;border-top:1px solid #edf2f7;">
        &copy; Gold Price Today. All rights reserved.
      </div>
    </div>
  </body>
</html>"""
    text_body = (
        f"อัปเดตผลพยากรณ์ถึงวันเป้าหมายแล้ว\n"
        f"วันที่เป้าหมาย: {target_date_display}\n"
        f"ผลการประเมิน: {status_text}\n"
        f"ช่วงพยากรณ์: ฿{pred_min:,.2f} - ฿{pred_max:,.2f}\n"
        f"ราคาจริง (ขายออก): ฿{actual_sell:,.2f}\n"
        f"ราคาจริง (รับซื้อ): ฿{actual_buy:,.2f}\n"
    )
    return _send_smtp(cfg, to_email, subject, text_body, html_body, user_id=user_id)


def send_verification_email(email: str, name: str, token: str, user_id: int = None) -> bool:
    """Send responsive HTML email verification link to user."""
    cfg = _smtp_config()
    to_email = (email or "").strip()
    safe_name = html.escape(str(name or "ผู้ใช้งาน").strip())
    base_url = _app_base_url()
    verify_url = f"{base_url}/api/auth/verify-email?token={token}"
    subject = "✉️ ยืนยันที่อยู่อีเมลของคุณ | Gold Price Today"

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ยืนยันที่อยู่อีเมลของคุณ</title>
</head>
<body style="font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background-color:#f4f6f9;margin:0;padding:24px;color:#333;">
  <div style="max-width:600px;margin:0 auto;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,0.08);border:1px solid #e2e8f0;">
    <div style="background:linear-gradient(135deg,#d4af37,#b8860b);padding:24px 30px;text-align:center;color:#ffffff;">
      <h1 style="margin:0;font-size:22px;font-weight:700;letter-spacing:0.5px;">✉️ ยืนยันที่อยู่อีเมลของคุณ</h1>
      <p style="margin:6px 0 0 0;font-size:14px;opacity:0.9;">Gold Price Today</p>
    </div>
    <div style="padding:30px;">
      <p style="font-size:16px;line-height:1.6;margin-top:0;">สวัสดีคุณ <strong>{safe_name}</strong>,</p>
      <p style="font-size:15px;line-height:1.6;color:#555;">ขอบคุณที่สมัครใช้งานระบบวิเคราะห์และแจ้งเตือนราคาทองคำ กรุณาคลิกปุ่มด้านล่างเพื่อยืนยันที่อยู่อีเมลของคุณ:</p>
      <div style="text-align:center;margin:30px 0;">
        <a href="{verify_url}" style="background:linear-gradient(135deg,#d4af37,#b8860b);color:#ffffff;text-decoration:none;padding:14px 32px;font-size:16px;font-weight:bold;border-radius:8px;display:inline-block;box-shadow:0 2px 6px rgba(212,175,55,0.4);">
          ยืนยันอีเมลตอนนี้
        </a>
      </div>
      <p style="font-size:13px;color:#718096;line-height:1.5;">หรือคัดลอกโทเค็นนี้ไปใช้งาน: <code style="background:#edf2f7;padding:4px 8px;border-radius:4px;font-size:13px;word-break:break-all;">{token}</code></p>
      <p style="font-size:13px;color:#718096;line-height:1.5;">ลิงก์นี้จะหมดอายุภายใน 24 ชั่วโมง หากคุณไม่ได้ร้องขอ โปรดเพิกเฉยต่ออีเมลฉบับนี้</p>
    </div>
    <div style="background:#fafafa;padding:16px 30px;text-align:center;font-size:12px;color:#a0aec0;border-top:1px solid #edf2f7;">
      &copy; Gold Price Today. All rights reserved.
    </div>
  </div>
</body>
</html>"""

    text_body = (
        f"ยืนยันที่อยู่อีเมลของคุณ | Gold Price Today\n\n"
        f"สวัสดีคุณ {safe_name},\n"
        f"กรุณายืนยันที่อยู่อีเมลของคุณโดยคลิกลิงก์ด้านล่าง:\n"
        f"{verify_url}\n\n"
        f"หรือใช้โทเค็น: {token}\n"
        f"(ลิงก์นี้จะหมดอายุภายใน 24 ชั่วโมง)\n"
    )
    return _send_smtp(cfg, to_email, subject, text_body, html_body, user_id=user_id)


def send_password_reset_email(email: str, name: str, token: str, user_id: int = None) -> bool:
    """Send responsive HTML password reset link to user."""
    cfg = _smtp_config()
    to_email = (email or "").strip()
    safe_name = html.escape(str(name or "ผู้ใช้งาน").strip())
    base_url = _app_base_url()
    reset_url = f"{base_url}/reset-password.html?token={token}"
    subject = "🔐 รีเซ็ตรหัสผ่านของคุณ | Gold Price Today"

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>รีเซ็ตรหัสผ่านของคุณ</title>
</head>
<body style="font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background-color:#f4f6f9;margin:0;padding:24px;color:#333;">
  <div style="max-width:600px;margin:0 auto;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,0.08);border:1px solid #e2e8f0;">
    <div style="background:linear-gradient(135deg,#d4af37,#b8860b);padding:24px 30px;text-align:center;color:#ffffff;">
      <h1 style="margin:0;font-size:22px;font-weight:700;letter-spacing:0.5px;">🔐 รีเซ็ตรหัสผ่านของคุณ</h1>
      <p style="margin:6px 0 0 0;font-size:14px;opacity:0.9;">Gold Price Today</p>
    </div>
    <div style="padding:30px;">
      <p style="font-size:16px;line-height:1.6;margin-top:0;">สวัสดีคุณ <strong>{safe_name}</strong>,</p>
      <p style="font-size:15px;line-height:1.6;color:#555;">เราได้รับคำขอรีเซ็ตรหัสผ่านสำหรับบัญชีของคุณ คลิกปุ่มด้านล่างเพื่อตั้งรหัสผ่านใหม่:</p>
      <div style="text-align:center;margin:30px 0;">
        <a href="{reset_url}" style="background:linear-gradient(135deg,#d4af37,#b8860b);color:#ffffff;text-decoration:none;padding:14px 32px;font-size:16px;font-weight:bold;border-radius:8px;display:inline-block;box-shadow:0 2px 6px rgba(212,175,55,0.4);">
          ตั้งรหัสผ่านใหม่
        </a>
      </div>
      <p style="font-size:13px;color:#718096;line-height:1.5;">หรือใช้โทเค็นรีเซ็ตนี้: <code style="background:#edf2f7;padding:4px 8px;border-radius:4px;font-size:13px;word-break:break-all;">{token}</code></p>
      <p style="font-size:13px;color:#e53e3e;line-height:1.5;margin-top:16px;"><strong>⚠️ ข้อควรระวังด้านความปลอดภัย:</strong> ลิงก์นี้จะหมดอายุภายใน 1 ชั่วโมง หากคุณไม่ได้ทำรายการ บัญชีของคุณยังคงปลอดภัยและสามารถเพิกเฉยต่ออีเมลนี้ได้</p>
    </div>
    <div style="background:#fafafa;padding:16px 30px;text-align:center;font-size:12px;color:#a0aec0;border-top:1px solid #edf2f7;">
      &copy; Gold Price Today. All rights reserved.
    </div>
  </div>
</body>
</html>"""

    text_body = (
        f"รีเซ็ตรหัสผ่านของคุณ | Gold Price Today\n\n"
        f"สวัสดีคุณ {safe_name},\n"
        f"คลิกลิงก์ด้านล่างเพื่อตั้งรหัสผ่านใหม่:\n"
        f"{reset_url}\n\n"
        f"หรือใช้โทเค็น: {token}\n"
        f"(ลิงก์นี้จะหมดอายุภายใน 1 ชั่วโมง)\n"
    )
    return _send_smtp(cfg, to_email, subject, text_body, html_body, user_id=user_id)


def send_morning_price_summary_email_smtp(email: str, name: str, bar_sell: float, bar_buy: float, world_usd: float = None, user_id: int = None) -> bool:
    """Send responsive HTML daily morning price summary to opted-in users."""
    cfg = _smtp_config()
    to_email = (email or "").strip()
    safe_name = html.escape(str(name or "นักลงทุน").strip())
    subject = "🌅 สรุปราคาทองคำเช้านี้ | Gold Price Today"
    world_text = f"${float(world_usd):,.2f}/oz" if world_usd else "N/A"

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>สรุปราคาทองคำเช้านี้</title>
</head>
<body style="font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background-color:#f4f6f9;margin:0;padding:24px;color:#333;">
  <div style="max-width:600px;margin:0 auto;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,0.08);border:1px solid #e2e8f0;">
    <div style="background:linear-gradient(135deg,#d4af37,#b8860b);padding:24px 30px;text-align:center;color:#ffffff;">
      <h1 style="margin:0;font-size:22px;font-weight:700;letter-spacing:0.5px;">🌅 สรุปราคาทองคำประจำวัน</h1>
      <p style="margin:6px 0 0 0;font-size:14px;opacity:0.9;">Gold Price Today</p>
    </div>
    <div style="padding:30px;">
      <p style="font-size:16px;line-height:1.6;margin-top:0;">สวัสดีคุณ <strong>{safe_name}</strong>,</p>
      <p style="font-size:15px;line-height:1.6;color:#555;">สรุปรายงานราคาทองคำช่วงเปิดตลาดเช้าวันนี้:</p>
      <div style="background:#f7fafc;border:1px solid #e2e8f0;border-radius:8px;padding:20px;margin:20px 0;">
        <p style="margin:8px 0;font-size:15px;"><strong>ทองคำแท่ง (ขายออก):</strong> <span style="color:#b8860b;font-weight:bold;font-size:17px;">฿{float(bar_sell or 0):,.2f}</span></p>
        <p style="margin:8px 0;font-size:15px;"><strong>ทองคำแท่ง (รับซื้อ):</strong> <span style="color:#2d3748;font-weight:bold;">฿{float(bar_buy or 0):,.2f}</span></p>
        <p style="margin:8px 0;font-size:15px;"><strong>World Spot:</strong> <span style="color:#2b6cb0;font-weight:bold;">{world_text}</span></p>
      </div>
      <p style="font-size:13px;color:#718096;line-height:1.5;">ติดตามการวิเคราะห์แนวโน้มและพยากรณ์ราคาเพิ่มเติมได้ที่ระบบ Gold Price Today</p>
    </div>
    <div style="background:#fafafa;padding:16px 30px;text-align:center;font-size:12px;color:#a0aec0;border-top:1px solid #edf2f7;">
      &copy; Gold Price Today. All rights reserved.
    </div>
  </div>
</body>
</html>"""

    text_body = (
        f"🌅 สรุปราคาทองคำเช้านี้ | Gold Price Today\n\n"
        f"สวัสดีคุณ {safe_name},\n"
        f"- ทองคำแท่ง (ขายออก): ฿{float(bar_sell or 0):,.2f}\n"
        f"- ทองคำแท่ง (รับซื้อ): ฿{float(bar_buy or 0):,.2f}\n"
        f"- World Spot: {world_text}\n"
    )
    return _send_smtp(cfg, to_email, subject, text_body, html_body, user_id=user_id)

