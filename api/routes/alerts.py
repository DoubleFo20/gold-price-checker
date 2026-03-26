"""routes/alerts.py — Price alert CRUD endpoints."""
import traceback
import pymysql
from flask import Blueprint, jsonify, request
from database.connection import get_db_connection
from services.auth import _require_auth_user

alerts_bp = Blueprint("alerts", __name__)


# ---- New clean /api/alerts/* endpoints ----

@alerts_bp.route("/api/alerts/create", methods=["POST", "OPTIONS"])
def create_alert():
    if request.method == "OPTIONS":
        return jsonify(success=True)
    try:
        data = request.json
        if not data:
            return jsonify(success=False, message="No data provided"), 400
        target_price = float(data.get("target_price", 0))
        gold_type = data.get("gold_type", "bar")
        alert_type = data.get("alert_type", "above")
        email = data.get("email", "")
        if target_price <= 0 or not email:
            return jsonify(success=False, message="Invalid parameters"), 400
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM users WHERE email=%s", (email,))
                user_row = cursor.fetchone()
                if not user_row:
                    return jsonify(success=False, message="User not found. Please register first."), 404
                cursor.execute(
                    "INSERT INTO price_alerts (user_id, target_price, gold_type, alert_type, channel_email, notify_email) VALUES (%s, %s, %s, %s, 1, %s)",
                    (user_row["id"], target_price, gold_type, alert_type, email),
                )
            conn.commit()
            return jsonify(success=True, message="Alert saved successfully")
        finally:
            conn.close()
    except Exception as e:
        if isinstance(e, pymysql.err.IntegrityError):
            return jsonify(success=False, message="มีการตั้งค่าแจ้งเตือนนี้แล้ว"), 409
        traceback.print_exc()
        return jsonify(success=False, message=str(e)), 500


@alerts_bp.route("/api/alerts", methods=["GET", "OPTIONS"])
def list_alerts():
    if request.method == "OPTIONS":
        return jsonify(success=True)
    try:
        email = request.args.get("email", "")
        if not email:
            return jsonify(success=False, message="Email required"), 400
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, user_id, target_price, alert_type, gold_type, channel_email, notify_email, triggered, triggered_at, created_at FROM price_alerts WHERE notify_email=%s ORDER BY created_at DESC",
                    (email,),
                )
                alerts = cursor.fetchall()
            return jsonify(success=True, items=alerts)
        finally:
            conn.close()
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, message=str(e)), 500


@alerts_bp.route("/api/alerts/<int:alert_id>", methods=["DELETE", "OPTIONS"])
def delete_alert(alert_id):
    if request.method == "OPTIONS":
        return jsonify(success=True)
    try:
        email = request.args.get("email", "")
        if not email:
            return jsonify(success=False, message="Email required"), 400
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM price_alerts WHERE id=%s AND notify_email=%s", (alert_id, email))
            conn.commit()
            return jsonify(success=True, message="Alert deleted successfully")
        finally:
            conn.close()
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, message=str(e)), 500


# ---- PHP-compat /api/api/alerts/* endpoints ----

@alerts_bp.route("/api/api/alerts/create.php", methods=["POST", "OPTIONS"])
def php_compat_alerts_create():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    data = request.get_json(silent=True) or {}
    target_price = data.get("target_price")
    alert_type = (data.get("alert_type") or "").strip()
    gold_type = (data.get("gold_type") or "bar").strip()
    email = (data.get("email") or "").strip()
    try:
        target_price = float(target_price)
    except Exception:
        target_price = None
    if not target_price or target_price <= 0 or alert_type not in ("above", "below") or gold_type not in ("bar", "ornament", "world"):
        return jsonify(success=False, message="ข้อมูลไม่ถูกต้อง"), 400
    conn = get_db_connection()
    try:
        user, err = _require_auth_user(conn)
        if err:
            return err
        with conn.cursor() as cursor:
            try:
                cursor.execute(
                    "INSERT INTO price_alerts (user_id, target_price, alert_type, gold_type, notify_email, channel_email, triggered) VALUES (%s, %s, %s, %s, %s, 1, 0)",
                    (user["id"], target_price, alert_type, gold_type, email or user.get("email")),
                )
            except Exception:
                cursor.execute(
                    "INSERT INTO price_alerts (user_id, target_price, alert_type, gold_type, email, triggered) VALUES (%s, %s, %s, %s, %s, 0)",
                    (user["id"], target_price, alert_type, gold_type, email or user.get("email")),
                )
        conn.commit()
        return jsonify(success=True, message="ตั้งค่าการแจ้งเตือนสำเร็จ"), 200
    except pymysql.err.IntegrityError:
        return jsonify(success=False, message="มีรายการแจ้งเตือนนี้อยู่แล้ว"), 409
    except Exception:
        traceback.print_exc()
        return jsonify(success=False, message="ไม่สามารถบันทึกการแจ้งเตือนได้"), 500
    finally:
        conn.close()


@alerts_bp.route("/api/api/alerts/list.php", methods=["GET", "OPTIONS"])
def php_compat_alerts_list():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    conn = get_db_connection()
    try:
        user, err = _require_auth_user(conn)
        if err:
            return err
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM price_alerts WHERE user_id=%s ORDER BY created_at DESC", (user["id"],))
            items = cursor.fetchall() or []
        return jsonify(success=True, items=items), 200
    except Exception:
        traceback.print_exc()
        return jsonify(success=False, message="โหลดไม่สำเร็จ"), 500
    finally:
        conn.close()


@alerts_bp.route("/api/api/alerts/delete.php", methods=["POST", "OPTIONS"])
def php_compat_alerts_delete():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    data = request.get_json(silent=True) or {}
    alert_id = data.get("id")
    try:
        alert_id = int(alert_id)
    except Exception:
        return jsonify(success=False, message="Invalid ID"), 400
    conn = get_db_connection()
    try:
        user, err = _require_auth_user(conn)
        if err:
            return err
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM price_alerts WHERE id=%s AND user_id=%s", (alert_id, user["id"]))
        conn.commit()
        return jsonify(success=True, message="Deleted"), 200
    except Exception:
        traceback.print_exc()
        return jsonify(success=False, message="Delete failed"), 500
    finally:
        conn.close()
