"""routes/auth_routes.py — Compat routes for /api/api/auth/* PHP-style endpoints."""
import os
import time
import traceback
from datetime import datetime

from flask import Blueprint, jsonify, request

from database.connection import get_db_connection, _retry_after_users_column_fix
from services.auth import _auth_get_user_by_session, _require_auth_user
from utils.helpers import _cookie_secure, _bcrypt_verify, _bcrypt_hash

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/api/api/auth/login.php", methods=["POST", "OPTIONS"])
def php_compat_login():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify(success=False, message="กรุณากรอกอีเมลและรหัสผ่าน"), 400
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email=%s AND is_active=1 LIMIT 1", (email,))
            user = cursor.fetchone()
        if not user or not _bcrypt_verify(password, user.get("password_hash") or ""):
            return jsonify(success=False, message="อีเมลหรือรหัสผ่านไม่ถูกต้อง"), 401
        token = os.urandom(32).hex()
        expires_ts = int(time.time()) + (86400 * 7)
        expires_at_db = datetime.fromtimestamp(expires_ts).strftime("%Y-%m-%d %H:%M:%S")
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO sessions (user_id, token, expires_at, ip_address, user_agent) VALUES (%s, %s, %s, %s, %s)",
                (user["id"], token, expires_at_db,
                 request.headers.get("X-Forwarded-For", request.remote_addr),
                 request.headers.get("User-Agent", "")[:1000]),
            )
        conn.commit()
        resp = jsonify(success=True, message="เข้าสู่ระบบสำเร็จ!", user={k: v for k, v in user.items() if k != "password_hash"})
        resp.set_cookie("session_token", token, expires=expires_ts, path="/", secure=_cookie_secure(), httponly=True, samesite="Lax")
        return resp, 200
    except Exception:
        traceback.print_exc()
        return jsonify(success=False, message="Server error while processing login."), 500
    finally:
        conn.close()


@auth_bp.route("/api/api/auth/register.php", methods=["POST", "OPTIONS"])
def php_compat_register():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip()
    if (not email) or ("@" not in email) or (not name) or (not password) or (len(password) < 6):
        return jsonify(success=False, message="ข้อมูลไม่ถูกต้อง กรุณากรอกข้อมูลให้ครบถ้วน"), 400
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE email=%s LIMIT 1", (email,))
            if cursor.fetchone():
                return jsonify(success=False, message="อีเมลนี้ถูกใช้งานแล้ว"), 409
            pw_hash = _bcrypt_hash(password)
            cursor.execute(
                "INSERT INTO users (email, password_hash, name, role, is_active) VALUES (%s, %s, %s, 'user', 1)",
                (email, pw_hash, name),
            )
        conn.commit()
        return jsonify(success=True, message="สมัครสมาชิกสำเร็จ! กรุณาเข้าสู่ระบบ"), 201
    except Exception:
        traceback.print_exc()
        return jsonify(success=False, message="เกิดข้อผิดพลาดในการสมัครสมาชิก"), 500
    finally:
        conn.close()


@auth_bp.route("/api/api/auth/check_session.php", methods=["POST", "OPTIONS"])
def php_compat_check_session():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    token = request.cookies.get("session_token") or ""
    conn = get_db_connection()
    try:
        user = _auth_get_user_by_session(conn, token)
        if user:
            return jsonify(success=True, authenticated=True, user={k: v for k, v in user.items() if k != "password_hash"}), 200
        resp = jsonify(success=True, authenticated=False)
        resp.set_cookie("session_token", "", expires=0, path="/")
        return resp, 200
    except Exception:
        traceback.print_exc()
        return jsonify(success=False, authenticated=False, message="Server error during session check"), 500
    finally:
        conn.close()


@auth_bp.route("/api/api/auth/update_profile.php", methods=["POST", "OPTIONS"])
def php_compat_update_profile():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if len(name) < 2:
        return jsonify(success=False, message="ชื่อไม่ถูกต้อง"), 400
    conn = get_db_connection()
    try:
        user, err = _require_auth_user(conn)
        if err:
            return err
        def _save_name():
            with conn.cursor() as cursor:
                cursor.execute("UPDATE users SET name=%s WHERE id=%s", (name, user["id"]))
            conn.commit()
        _retry_after_users_column_fix(conn, ("name",), _save_name)
        return jsonify(success=True, message="อัปเดตโปรไฟล์สำเร็จ", user={"id": user["id"], "name": name, "email": user.get("email")}), 200
    except Exception:
        traceback.print_exc()
        return jsonify(success=False, message="ไม่สามารถบันทึกชื่อได้"), 500
    finally:
        conn.close()


@auth_bp.route("/api/api/auth/change_password.php", methods=["POST", "OPTIONS"])
def php_compat_change_password():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    data = request.get_json(silent=True) or {}
    old_password = data.get("old_password") or ""
    new_password = data.get("new_password") or ""
    if (not old_password) or len(new_password) < 6:
        return jsonify(success=False, message="ข้อมูลไม่ถูกต้อง"), 400
    conn = get_db_connection()
    try:
        user, err = _require_auth_user(conn)
        if err:
            return err
        with conn.cursor() as cursor:
            cursor.execute("SELECT password_hash FROM users WHERE id=%s LIMIT 1", (user["id"],))
            row = cursor.fetchone() or {}
        if not _bcrypt_verify(old_password, row.get("password_hash") or ""):
            return jsonify(success=False, message="รหัสผ่านเดิมไม่ถูกต้อง"), 400
        new_hash = _bcrypt_hash(new_password)
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET password_hash=%s WHERE id=%s", (new_hash, user["id"]))
        conn.commit()
        return jsonify(success=True, message="เปลี่ยนรหัสผ่านสำเร็จ"), 200
    except Exception:
        traceback.print_exc()
        return jsonify(success=False, message="ไม่สามารถเปลี่ยนรหัสผ่านได้"), 500
    finally:
        conn.close()


@auth_bp.route("/api/api/auth/logout.php", methods=["POST", "OPTIONS"])
def php_compat_logout():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    token = request.cookies.get("session_token") or ""
    conn = get_db_connection()
    try:
        if token:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM sessions WHERE token=%s", (token,))
            conn.commit()
        resp = jsonify(success=True, message="Logged out")
        resp.set_cookie("session_token", "", expires=0, path="/")
        return resp, 200
    except Exception:
        traceback.print_exc()
        resp = jsonify(success=False, message="Logout failed")
        resp.set_cookie("session_token", "", expires=0, path="/")
        return resp, 500
    finally:
        conn.close()
