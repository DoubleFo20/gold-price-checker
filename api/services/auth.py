"""services/auth.py — Session and authentication helpers."""
from flask import request
from database.connection import get_db_connection


def _auth_get_user_by_session(conn, token: str):
    if not token:
        return None
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT u.*
            FROM sessions s
            INNER JOIN users u ON u.id = s.user_id
            WHERE s.token = %s AND s.expires_at > NOW() AND u.is_active = 1
            LIMIT 1
            """,
            (token,),
        )
        return cursor.fetchone()


def _require_auth_user(conn):
    from flask import jsonify
    token = request.cookies.get("session_token") or ""
    user = _auth_get_user_by_session(conn, token)
    if not user:
        return None, (jsonify(success=False, message="กรุณาเข้าสู่ระบบ"), 401)
    return user, None
