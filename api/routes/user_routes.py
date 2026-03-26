"""routes/user_routes.py — Profile, notifications, forecasts, LINE code endpoints."""
import random
import json
import traceback
from flask import Blueprint, jsonify, request
from database.connection import get_db_connection, _retry_after_users_column_fix
from services.auth import _require_auth_user, _auth_get_user_by_session
from services.line_service import _line_connect_meta

user_bp = Blueprint("user", __name__)


@user_bp.route("/api/api/profile/update_push.php", methods=["POST", "OPTIONS"])
def php_compat_update_push():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    token = request.cookies.get("session_token") or ""
    conn = get_db_connection()
    try:
        user = _auth_get_user_by_session(conn, token)
        if not user:
            return jsonify(success=False, message="กรุณาเข้าสู่ระบบ"), 401
        sub = request.get_json(silent=True)
        sub_str = None if sub is None else json.dumps(sub, ensure_ascii=False)
        def _save_push():
            with conn.cursor() as cursor:
                cursor.execute("UPDATE users SET push_subscription=%s WHERE id=%s", (sub_str, user["id"]))
            conn.commit()
        try:
            _retry_after_users_column_fix(conn, ("push_subscription",), _save_push)
        except Exception as e:
            conn.rollback()
            return jsonify(success=False, message=str(e)), 500
        return jsonify(success=True, message="Subscription updated"), 200
    finally:
        conn.close()


@user_bp.route("/api/api/profile/generate_line_code.php", methods=["POST", "OPTIONS"])
def php_compat_generate_line_code():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    conn = get_db_connection()
    try:
        user, err = _require_auth_user(conn)
        if err:
            return err
        code = str(random.randint(0, 999999)).zfill(6)
        def _save_line_code():
            with conn.cursor() as cursor:
                cursor.execute("UPDATE users SET verification_token=%s WHERE id=%s", (code, user["id"]))
            conn.commit()
        _retry_after_users_column_fix(conn, ("verification_token",), _save_line_code)
        return jsonify(success=True, code=code, message="Code generated successfully", **_line_connect_meta()), 200
    except Exception:
        traceback.print_exc()
        return jsonify(success=False, message="Server Error"), 500
    finally:
        conn.close()


@user_bp.route("/api/api/profile/update_line.php", methods=["POST", "OPTIONS"])
def php_compat_update_line():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    data = request.get_json(silent=True) or {}
    line_id = data.get("line_user_id")
    display_name = data.get("display_name")
    conn = get_db_connection()
    try:
        user, err = _require_auth_user(conn)
        if err:
            return err
        def _save_line():
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET line_user_id=%s, line_display_name=%s WHERE id=%s",
                    (line_id, display_name, user["id"]),
                )
            conn.commit()
        _retry_after_users_column_fix(conn, ("line_user_id", "line_display_name"), _save_line)
        return jsonify(success=True, message="เชื่อมต่อ LINE สำเร็จ"), 200
    except Exception:
        traceback.print_exc()
        return jsonify(success=False, message="Server Error"), 500
    finally:
        conn.close()


@user_bp.route("/api/api/user/save_forecast.php", methods=["POST", "OPTIONS"])
def php_compat_save_forecast():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    from datetime import datetime
    data = request.get_json(silent=True) or {}
    target_date = (data.get("target_date") or "")[:10]
    trend = (data.get("trend") or "").strip()
    max_price = data.get("max_price")
    min_price = data.get("min_price")
    confidence = data.get("confidence")
    hist_days = data.get("hist_days")
    try:
        max_price = float(max_price); min_price = float(min_price)
        confidence = float(confidence); hist_days = int(hist_days)
    except Exception:
        return jsonify(success=False, message="ข้อมูลไม่ถูกต้อง"), 400
    if not target_date or not trend:
        return jsonify(success=False, message="ข้อมูลไม่ถูกต้อง"), 400
    conn = get_db_connection()
    try:
        user, err = _require_auth_user(conn)
        if err:
            return err
        forecast_date = datetime.now().strftime("%Y-%m-%d")
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO saved_forecasts (user_id, forecast_date, target_date, trend, max_price, min_price, confidence, hist_days) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (user["id"], forecast_date, target_date, trend, max_price, min_price, confidence, hist_days),
            )
        conn.commit()
        return jsonify(success=True, message="บันทึกสำเร็จ!"), 200
    except Exception:
        traceback.print_exc()
        return jsonify(success=False, message="บันทึกไม่สำเร็จ"), 500
    finally:
        conn.close()


@user_bp.route("/api/api/user/get_saved_forecasts.php", methods=["GET", "OPTIONS"])
def php_compat_get_saved_forecasts():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    conn = get_db_connection()
    try:
        user, err = _require_auth_user(conn)
        if err:
            return err
        with conn.cursor() as cursor:
            try:
                cursor.execute(
                    "SELECT id, user_id, forecast_date, target_date, trend, max_price, min_price, confidence, hist_days, actual_max_price, actual_min_price, verified_at, created_at FROM saved_forecasts WHERE user_id=%s ORDER BY created_at DESC LIMIT 100",
                    (user["id"],),
                )
            except Exception:
                cursor.execute(
                    "SELECT * FROM saved_forecasts WHERE user_id=%s ORDER BY created_at DESC LIMIT 100",
                    (user["id"],),
                )
            rows = cursor.fetchall() or []
        return jsonify(success=True, data=rows), 200
    except Exception:
        traceback.print_exc()
        return jsonify(success=False, message="โหลดไม่สำเร็จ"), 500
    finally:
        conn.close()


@user_bp.route("/api/api/notifications/list.php", methods=["GET", "OPTIONS"])
def php_compat_notifications_list():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    try:
        conn = get_db_connection()
    except Exception:
        traceback.print_exc()
        return jsonify(success=True, data=[], unread_count=0, degraded=True), 200
    try:
        user, err = _require_auth_user(conn)
        if err:
            return err
        with conn.cursor() as cursor:
            degraded = False
            try:
                cursor.execute(
                    "SELECT id, title, message, type, is_read, link, created_at FROM notifications WHERE user_id=%s ORDER BY created_at DESC LIMIT 20",
                    (user["id"],),
                )
                items = cursor.fetchall() or []
                cursor.execute("SELECT COUNT(*) AS c FROM notifications WHERE user_id=%s AND is_read=0", (user["id"],))
                unread = cursor.fetchone() or {"c": 0}
            except Exception:
                traceback.print_exc()
                items = []; unread = {"c": 0}; degraded = True
        return jsonify(success=True, data=items, unread_count=int(unread.get("c") or 0), degraded=degraded), 200
    except Exception:
        traceback.print_exc()
        return jsonify(success=True, data=[], unread_count=0, degraded=True), 200
    finally:
        conn.close()


@user_bp.route("/api/api/notifications/mark_read.php", methods=["POST", "OPTIONS"])
def php_compat_notifications_mark_read():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    data = request.get_json(silent=True) or {}
    notif_id = data.get("id")
    try:
        conn = get_db_connection()
    except Exception:
        traceback.print_exc()
        return jsonify(success=True, message="Notification storage unavailable", degraded=True), 200
    try:
        user, err = _require_auth_user(conn)
        if err:
            return err
        with conn.cursor() as cursor:
            if notif_id == "all":
                cursor.execute("UPDATE notifications SET is_read=1 WHERE user_id=%s", (user["id"],))
            else:
                try:
                    nid = int(notif_id)
                except Exception:
                    return jsonify(success=False, message="Invalid ID"), 400
                cursor.execute("UPDATE notifications SET is_read=1 WHERE id=%s AND user_id=%s", (nid, user["id"]))
        conn.commit()
        return jsonify(success=True, message="Updated successfully"), 200
    except Exception:
        traceback.print_exc()
        return jsonify(success=True, message="Notification storage unavailable", degraded=True), 200
    finally:
        conn.close()
