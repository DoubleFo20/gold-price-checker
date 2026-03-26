"""services/email_service.py — SMTP email senders."""
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


def _send_smtp(cfg, to_email, subject, text_body, html_body) -> bool:
    if not cfg["host"] or not cfg["user"] or not cfg["password"] or not cfg["from_email"]:
        print("SMTP config incomplete. Skipping.")
        return False
    if not to_email:
        print("No recipient email.")
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
        return True
    except Exception as e:
        print(f"SMTP send failed to {to_email}: {e}")
        return False


def send_alert_email_smtp(alert, current_price) -> bool:
    cfg = _smtp_config()
    to_email = (alert.get("receiver_email") or alert.get("notify_email") or alert.get("email") or "").strip()
    ptype = alert.get("gold_type", "bar")
    atype = alert.get("alert_type", "above")
    target_price = float(alert.get("target_price") or 0)
    user_name = alert.get("name") or "ลูกค้า"
    type_map = {"bar": "ทองคำแท่ง", "ornament": "ทองรูปพรรณ", "world": "ทองโลก (USD/oz)"}
    type_text = type_map.get(ptype, ptype)
    condition_text = "สูงกว่า หรือ เท่ากับ" if atype == "above" else "ต่ำกว่า หรือ เท่ากับ"
    money_prefix = "$" if ptype == "world" else "฿"
    current_text = f"{current_price:,.2f}"
    target_text = f"{target_price:,.2f}"
    subject = f"🔔 แจ้งเตือนราคาทอง: {type_text}"

    html_body = f"""
    <html>
      <body style="font-family:Arial,sans-serif;background:#f8f8f8;padding:16px;">
        <div style="max-width:640px;margin:auto;background:#fff;border:1px solid #eee;border-radius:10px;overflow:hidden;">
          <div style="background:linear-gradient(135deg,#d4af37,#b8860b);color:#fff;padding:16px 20px;">
            <h2 style="margin:0;">🔔 ระบบแจ้งเตือนราคาทอง</h2>
          </div>
          <div style="padding:20px;color:#333;">
            <p>สวัสดี คุณ{user_name}</p>
            <p>{type_text} ถึงเงื่อนไข <strong>{condition_text}</strong> ที่คุณตั้งไว้แล้ว</p>
            <p><strong>ราคาปัจจุบัน:</strong> {money_prefix}{current_text}</p>
            <p><strong>ราคาเป้าหมาย:</strong> {money_prefix}{target_text}</p>
            <p style="margin-top:20px;">เปิดดูรายละเอียดเพิ่มเติมได้ที่เว็บไซต์ Gold Price Today</p>
          </div>
        </div>
      </body>
    </html>
    """
    text_body = (
        f"แจ้งเตือนราคาทอง\n"
        f"ประเภท: {type_text}\n"
        f"เงื่อนไข: {condition_text}\n"
        f"ราคาปัจจุบัน: {money_prefix}{current_text}\n"
        f"ราคาเป้าหมาย: {money_prefix}{target_text}\n"
    )
    return _send_smtp(cfg, to_email, subject, text_body, html_body)


def send_forecast_email_smtp(payload) -> bool:
    cfg = _smtp_config()
    to_email = (payload.get("email") or "").strip()
    user_name = (payload.get("name") or "ลูกค้า").strip()
    target_date_raw = str(payload.get("target_date") or "").strip()
    trend = str(payload.get("trend") or "-")
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
    html_body = f"""
    <html>
      <body style="font-family:Arial,sans-serif;background:#f8f8f8;padding:16px;">
        <div style="max-width:680px;margin:auto;background:#fff;border:1px solid #eee;border-radius:10px;overflow:hidden;">
          <div style="background:linear-gradient(135deg,#d4af37,#b8860b);color:#fff;padding:16px 20px;">
            <h2 style="margin:0;">📈 บันทึกพยากรณ์ราคาทองคำสำเร็จ</h2>
          </div>
          <div style="padding:20px;color:#333;">
            <p>สวัสดี คุณ{user_name}</p>
            <p><strong>พยากรณ์สำหรับวันที่:</strong> {target_date_display}</p>
            <p><strong>แนวโน้ม:</strong> {trend}</p>
            <p><strong>ราคามากสุด (พยากรณ์):</strong> ฿{max_price:,.2f}</p>
            <p><strong>ราคาน้อยสุด (พยากรณ์):</strong> ฿{min_price:,.2f}</p>
            <p><strong>ความเชื่อมั่น (R²):</strong> {confidence:.2f}%</p>
            <p><strong>ข้อมูลย้อนหลังที่ใช้:</strong> {hist_days} วัน</p>
          </div>
        </div>
      </body>
    </html>
    """
    text_body = (
        f"บันทึกพยากรณ์ราคาทองคำสำเร็จ\n"
        f"พยากรณ์สำหรับวันที่: {target_date_display}\n"
        f"แนวโน้ม: {trend}\n"
        f"ราคามากสุด: ฿{max_price:,.2f}\n"
        f"ราคาน้อยสุด: ฿{min_price:,.2f}\n"
        f"ความเชื่อมั่น: {confidence:.2f}%\n"
        f"ข้อมูลย้อนหลังที่ใช้: {hist_days} วัน\n"
    )
    return _send_smtp(cfg, to_email, subject, text_body, html_body)


def send_forecast_result_email_smtp(payload) -> bool:
    cfg = _smtp_config()
    to_email = (payload.get("email") or "").strip()
    user_name = (payload.get("name") or "ลูกค้า").strip()
    target_date_display = payload.get("target_date_display") or "-"
    pred_min = float(payload.get("pred_min") or 0)
    pred_max = float(payload.get("pred_max") or 0)
    actual_buy = float(payload.get("actual_buy") or 0)
    actual_sell = float(payload.get("actual_sell") or 0)
    is_accurate = bool(payload.get("is_accurate"))
    status_text = "แม่นยำ ✅" if is_accurate else "ไม่แม่นยำ ❌"
    status_color = "#16A085" if is_accurate else "#e74c3c"

    subject = f"📊 ผลจริงพยากรณ์ทองคำ ({target_date_display}) {status_text}"
    html_body = f"""
    <html>
      <body style="font-family:Arial,sans-serif;background:#f8f8f8;padding:16px;">
        <div style="max-width:680px;margin:auto;background:#fff;border:1px solid #eee;border-radius:10px;overflow:hidden;">
          <div style="background:linear-gradient(135deg,#d4af37,#b8860b);color:#fff;padding:16px 20px;">
            <h2 style="margin:0;">📊 อัปเดตผลพยากรณ์ถึงวันเป้าหมายแล้ว</h2>
          </div>
          <div style="padding:20px;color:#333;">
            <p>สวัสดี คุณ{user_name}</p>
            <p><strong>พยากรณ์สำหรับวันที่:</strong> {target_date_display}</p>
            <p><strong>ผลการประเมิน:</strong> <span style="color:{status_color};font-weight:bold;">{status_text}</span></p>
            <p><strong>ช่วงพยากรณ์:</strong> ฿{pred_min:,.2f} - ฿{pred_max:,.2f}</p>
            <p><strong>ราคาจริง (ขายออก):</strong> ฿{actual_sell:,.2f}</p>
            <p><strong>ราคาจริง (รับซื้อ):</strong> ฿{actual_buy:,.2f}</p>
          </div>
        </div>
      </body>
    </html>
    """
    text_body = (
        f"อัปเดตผลพยากรณ์ถึงวันเป้าหมายแล้ว\n"
        f"วันที่เป้าหมาย: {target_date_display}\n"
        f"ผลการประเมิน: {status_text}\n"
        f"ช่วงพยากรณ์: ฿{pred_min:,.2f} - ฿{pred_max:,.2f}\n"
        f"ราคาจริง (ขายออก): ฿{actual_sell:,.2f}\n"
        f"ราคาจริง (รับซื้อ): ฿{actual_buy:,.2f}\n"
    )
    return _send_smtp(cfg, to_email, subject, text_body, html_body)
