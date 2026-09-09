"""routes/auth_routes.py — Compat routes for /api/api/auth/* PHP-style endpoints."""
import os
import secrets
import time
import traceback
from datetime import datetime, timedelta

from flask import Blueprint, abort, current_app, jsonify, request

from database.connection import get_db_connection, _retry_after_users_column_fix
from services.auth import _auth_get_user_by_session, _require_auth_user
from services.email_service import send_verification_email, send_password_reset_email
from utils.helpers import _client_ip, _cookie_secure, _bcrypt_verify, _bcrypt_hash
from utils.limiter import limiter

auth_bp = Blueprint("auth", __name__)


# ---------------------------------------------------------------------------
# Debug endpoint — test DB connectivity
# ---------------------------------------------------------------------------
@auth_bp.route("/api/debug/db", methods=["GET"])
def debug_db():
    """Quick endpoint to test if the database is reachable."""
    if current_app.config.get("ENV") == "production":
        abort(404)
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 AS ok")
                row = cursor.fetchone()
            return jsonify(success=True, db_ok=True, result=row), 200
        finally:
            conn.close()
    except Exception as exc:
        traceback.print_exc()
        return jsonify(success=False, db_ok=False, error=str(exc)), 500


@auth_bp.route("/api/auth/login", methods=["POST", "OPTIONS"])
@auth_bp.route("/api/auth/login.php", methods=["POST", "OPTIONS"])
@auth_bp.route("/api/api/auth/login.php", methods=["POST", "OPTIONS"])
@limiter.limit("5 per minute")
def php_compat_login():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify(success=False, message="กรุณากรอกอีเมลและรหัสผ่าน"), 400
    conn = None
    try:
        conn = get_db_connection()
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
                 _client_ip(request),
                 request.headers.get("User-Agent", "")[:1000]),
            )
        conn.commit()
        resp = jsonify(success=True, message="เข้าสู่ระบบสำเร็จ!", user={k: v for k, v in user.items() if k != "password_hash"})
        resp.set_cookie("session_token", token, expires=expires_ts, path="/", secure=_cookie_secure(), httponly=True, samesite="Lax")
        return resp, 200
    except Exception as exc:
        # Keep managed-database hosts and connection details out of the public
        # response; the exception type is sufficient for operational logs.
        current_app.logger.error(
            "Login database operation failed (%s)", type(exc).__name__,
        )
        return jsonify(
            success=False,
            message="ระบบฐานข้อมูลไม่พร้อมใช้งาน กรุณาลองใหม่อีกครั้งภายหลัง",
        ), 503
    finally:
        if conn:
            conn.close()


@auth_bp.route("/api/auth/register", methods=["POST", "OPTIONS"])
@auth_bp.route("/api/auth/register.php", methods=["POST", "OPTIONS"])
@auth_bp.route("/api/api/auth/register.php", methods=["POST", "OPTIONS"])
@limiter.limit("5 per minute")
def php_compat_register():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip()
    if (not email) or ("@" not in email) or (not name) or (not password) or (len(password) < 6):
        return jsonify(success=False, message="ข้อมูลไม่ถูกต้อง กรุณากรอกข้อมูลให้ครบถ้วน"), 400
    conn = None
    try:
        conn = get_db_connection()
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
    except Exception as exc:
        traceback.print_exc()
        return jsonify(success=False, message=f"เกิดข้อผิดพลาดในการสมัครสมาชิก: {str(exc)}"), 500
    finally:
        if conn:
            conn.close()


@auth_bp.route("/api/auth/check-session", methods=["POST", "OPTIONS"])
@auth_bp.route("/api/auth/check_session", methods=["POST", "OPTIONS"])
@auth_bp.route("/api/auth/check_session.php", methods=["POST", "OPTIONS"])
@auth_bp.route("/api/api/auth/check_session.php", methods=["POST", "OPTIONS"])
def php_compat_check_session():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    token = request.cookies.get("session_token") or ""
    conn = None
    try:
        conn = get_db_connection()
        user = _auth_get_user_by_session(conn, token)
        if user:
            return jsonify(success=True, authenticated=True, user={k: v for k, v in user.items() if k != "password_hash"}), 200
        resp = jsonify(success=True, authenticated=False)
        resp.set_cookie("session_token", "", expires=0, path="/")
        return resp, 200
    except Exception as exc:
        traceback.print_exc()
        return jsonify(success=False, authenticated=False, message=f"DB error: {str(exc)}"), 500
    finally:
        if conn:
            conn.close()


@auth_bp.route("/api/auth/update-profile", methods=["POST", "OPTIONS"])
@auth_bp.route("/api/auth/update_profile", methods=["POST", "OPTIONS"])
@auth_bp.route("/api/auth/update_profile.php", methods=["POST", "OPTIONS"])
@auth_bp.route("/api/api/auth/update_profile.php", methods=["POST", "OPTIONS"])
def php_compat_update_profile():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if len(name) < 2:
        return jsonify(success=False, message="ชื่อไม่ถูกต้อง"), 400
    conn = None
    try:
        conn = get_db_connection()
        user, err = _require_auth_user(conn)
        if err:
            return err
        def _save_name():
            with conn.cursor() as cursor:
                cursor.execute("UPDATE users SET name=%s WHERE id=%s", (name, user["id"]))
            conn.commit()
        _retry_after_users_column_fix(conn, ("name",), _save_name)
        return jsonify(success=True, message="อัปเดตโปรไฟล์สำเร็จ", user={"id": user["id"], "name": name, "email": user.get("email")}), 200
    except Exception as exc:
        traceback.print_exc()
        return jsonify(success=False, message=f"ไม่สามารถบันทึกชื่อได้: {str(exc)}"), 500
    finally:
        if conn:
            conn.close()


@auth_bp.route("/api/auth/change-password", methods=["POST", "OPTIONS"])
@auth_bp.route("/api/auth/change_password", methods=["POST", "OPTIONS"])
@auth_bp.route("/api/auth/change_password.php", methods=["POST", "OPTIONS"])
@auth_bp.route("/api/api/auth/change_password.php", methods=["POST", "OPTIONS"])
@limiter.limit("5 per minute")
def php_compat_change_password():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    data = request.get_json(silent=True) or {}
    old_password = data.get("old_password") or ""
    new_password = data.get("new_password") or ""
    if (not old_password) or len(new_password) < 6:
        return jsonify(success=False, message="ข้อมูลไม่ถูกต้อง"), 400
    conn = None
    try:
        conn = get_db_connection()
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
            # Immediately revoke all existing active sessions for this user
            cursor.execute("DELETE FROM sessions WHERE user_id=%s", (user["id"],))
        conn.commit()
        resp = jsonify(success=True, message="เปลี่ยนรหัสผ่านสำเร็จ กรุณาเข้าสู่ระบบใหม่")
        resp.set_cookie("session_token", "", expires=0, path="/", secure=_cookie_secure(), httponly=True, samesite="Lax")
        return resp, 200
    except Exception as exc:
        traceback.print_exc()
        return jsonify(success=False, message=f"ไม่สามารถเปลี่ยนรหัสผ่านได้: {str(exc)}"), 500
    finally:
        if conn:
            conn.close()


@auth_bp.route("/api/auth/logout", methods=["POST", "OPTIONS"])
@auth_bp.route("/api/auth/logout.php", methods=["POST", "OPTIONS"])
@auth_bp.route("/api/api/auth/logout.php", methods=["POST", "OPTIONS"])
def php_compat_logout():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    token = request.cookies.get("session_token") or ""
    conn = None
    try:
        conn = get_db_connection()
        if token:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM sessions WHERE token=%s", (token,))
            conn.commit()
        resp = jsonify(success=True, message="Logged out")
        resp.set_cookie("session_token", "", expires=0, path="/", secure=_cookie_secure(), httponly=True, samesite="Lax")
        return resp, 200
    except Exception as exc:
        traceback.print_exc()
        resp = jsonify(success=False, message=f"Logout failed: {str(exc)}")
        resp.set_cookie("session_token", "", expires=0, path="/", secure=_cookie_secure(), httponly=True, samesite="Lax")
        return resp, 500
    finally:
        if conn:
            conn.close()


def _ensure_password_resets_table(conn):
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS password_resets (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    token VARCHAR(128) NOT NULL UNIQUE,
                    expires_at DATETIME NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_token (token),
                    INDEX idx_user_id (user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )
        conn.commit()
    except Exception:
        pass


@auth_bp.route("/api/auth/forgot-password", methods=["POST", "OPTIONS"])
@auth_bp.route("/api/auth/forgot", methods=["POST", "OPTIONS"])
@auth_bp.route("/api/auth/forgot.php", methods=["POST", "OPTIONS"])
@auth_bp.route("/api/api/auth/forgot.php", methods=["POST", "OPTIONS"])
@limiter.limit("5 per minute")
def forgot_password():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    if not email:
        return jsonify(success=False, message="กรุณากรอกอีเมล"), 400
    conn = None
    try:
        conn = get_db_connection()
        _ensure_password_resets_table(conn)
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name, email FROM users WHERE email=%s LIMIT 1", (email,))
            user = cursor.fetchone()
        if user:
            token = secrets.token_urlsafe(32)
            expires_at = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO password_resets (user_id, token, expires_at) VALUES (%s, %s, %s)",
                    (user["id"], token, expires_at),
                )
            conn.commit()
            try:
                send_password_reset_email(user["email"], user.get("name", ""), token, user_id=user["id"])
            except Exception:
                traceback.print_exc()
        return jsonify(success=True, message="หากมีอีเมลนี้ในระบบ เราได้ส่งลิงก์รีเซ็ตรหัสผ่านแล้ว"), 200
    except Exception as exc:
        traceback.print_exc()
        return jsonify(success=False, message="เกิดข้อผิดพลาดในการร้องขอรีเซ็ตรหัสผ่าน"), 500
    finally:
        if conn:
            conn.close()


@auth_bp.route("/api/auth/reset-password", methods=["POST", "OPTIONS"])
@auth_bp.route("/api/auth/reset", methods=["POST", "OPTIONS"])
@auth_bp.route("/api/auth/reset.php", methods=["POST", "OPTIONS"])
@auth_bp.route("/api/api/auth/reset.php", methods=["POST", "OPTIONS"])
@limiter.limit("5 per minute")
def reset_password():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    new_password = data.get("new_password") or data.get("password") or ""
    if not token or len(new_password) < 6:
        return jsonify(success=False, message="โทเค็นหรือรหัสผ่านไม่ถูกต้อง (อย่างน้อย 6 ตัวอักษร)"), 400
    conn = None
    try:
        conn = get_db_connection()
        _ensure_password_resets_table(conn)
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, user_id, expires_at FROM password_resets WHERE token=%s AND expires_at > NOW() ORDER BY id DESC LIMIT 1",
                (token,),
            )
            reset_record = cursor.fetchone()
        if not reset_record:
            return jsonify(success=False, message="โทเค็นหมดอายุหรือไม่ถูกต้อง"), 400
        user_id = reset_record["user_id"]
        new_hash = _bcrypt_hash(new_password)
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET password_hash=%s WHERE id=%s", (new_hash, user_id))
            cursor.execute("DELETE FROM sessions WHERE user_id=%s", (user_id,))
            cursor.execute("DELETE FROM password_resets WHERE token=%s", (token,))
        conn.commit()
        return jsonify(success=True, message="รีเซ็ตรหัสผ่านสำเร็จ กรุณาเข้าสู่ระบบด้วยรหัสผ่านใหม่"), 200
    except Exception as exc:
        traceback.print_exc()
        return jsonify(success=False, message="เกิดข้อผิดพลาดในการรีเซ็ตรหัสผ่าน"), 500
    finally:
        if conn:
            conn.close()


@auth_bp.route("/api/auth/verify-email", methods=["GET", "POST", "OPTIONS"])
@auth_bp.route("/api/auth/verify", methods=["GET", "POST", "OPTIONS"])
@auth_bp.route("/api/auth/verify.php", methods=["GET", "POST", "OPTIONS"])
@auth_bp.route("/api/api/auth/verify.php", methods=["GET", "POST", "OPTIONS"])
def verify_email():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    data = request.get_json(silent=True) or {}
    token = (request.args.get("token") or data.get("token") or "").strip()
    if not token:
        return jsonify(success=False, message="กรุณาระบุโทเค็นยืนยันอีเมล"), 400
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, is_active FROM users WHERE verification_token=%s LIMIT 1", (token,))
            user = cursor.fetchone()
        if not user:
            return jsonify(success=False, message="โทเค็นไม่ถูกต้องหรือหมดอายุ"), 400
        with conn.cursor() as cursor:
            try:
                cursor.execute("UPDATE users SET is_verified=1, verification_token=NULL WHERE id=%s", (user["id"],))
            except Exception:
                cursor.execute("UPDATE users SET verification_token=NULL WHERE id=%s", (user["id"],))
        conn.commit()
        return jsonify(success=True, message="ยืนยันที่อยู่อีเมลสำเร็จเรียบร้อยแล้ว"), 200
    except Exception as exc:
        traceback.print_exc()
        return jsonify(success=False, message="เกิดข้อผิดพลาดในการยืนยันอีเมล"), 500
    finally:
        if conn:
            conn.close()


@auth_bp.route("/api/auth/resend-verify", methods=["POST", "OPTIONS"])
@auth_bp.route("/api/auth/resend_verify", methods=["POST", "OPTIONS"])
@auth_bp.route("/api/auth/resend_verify.php", methods=["POST", "OPTIONS"])
@auth_bp.route("/api/api/auth/resend_verify.php", methods=["POST", "OPTIONS"])
@limiter.limit("3 per minute")
def resend_verify():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    if not email:
        return jsonify(success=False, message="กรุณากรอกอีเมล"), 400
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name, email FROM users WHERE email=%s LIMIT 1", (email,))
            user = cursor.fetchone()
        if user:
            import random
            token = str(random.randint(100000, 999999))
            with conn.cursor() as cursor:
                cursor.execute("UPDATE users SET verification_token=%s WHERE id=%s", (token, user["id"]))
            conn.commit()
            try:
                send_verification_email(user["email"], user.get("name", ""), token, user_id=user["id"])
            except Exception:
                traceback.print_exc()
        return jsonify(success=True, message="หากมีอีเมลนี้ในระบบ เราได้ส่งรหัสยืนยันแล้ว"), 200
    except Exception as exc:
        traceback.print_exc()
        return jsonify(success=False, message="เกิดข้อผิดพลาดในการส่งรหัสยืนยัน"), 500
    finally:
        if conn:
            conn.close()
