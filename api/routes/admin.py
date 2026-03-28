"""routes/admin.py — Admin dashboard endpoints (v2 — full coverage)."""
import traceback
from flask import Blueprint, jsonify, request
from database.connection import get_db_connection
from services.auth import _require_auth_user

admin_bp = Blueprint("admin", __name__)


def _require_admin(conn):
    """Ensure the current session user has the 'admin' role."""
    user, err = _require_auth_user(conn)
    if err:
        return None, err
    if user.get("role") != "admin":
        return None, (jsonify(success=False, message="Unauthorized. Admin access required."), 403)
    return user, None


# ── Dashboard KPIs ───────────────────────────────────────────────────────────
@admin_bp.route("/api/admin/stats", methods=["GET"])
def admin_stats():
    conn = get_db_connection()
    try:
        user, err = _require_admin(conn)
        if err:
            return err

        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as c FROM users")
            users_count = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM price_alerts WHERE triggered=0")
            alerts_count = cursor.fetchone()["c"]

            try:
                cursor.execute("SELECT COUNT(*) as c FROM saved_forecasts")
                forecasts_count = cursor.fetchone()["c"]
            except Exception:
                forecasts_count = 0

        return jsonify(
            success=True,
            data={
                "users_count": users_count,
                "alerts_count": alerts_count,
                "forecasts_count": forecasts_count,
            }
        )
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, message=str(e)), 500
    finally:
        conn.close()


# ── Price History ─────────────────────────────────────────────────────────────
@admin_bp.route("/api/admin/price-history", methods=["GET"])
def admin_price_history():
    conn = get_db_connection()
    try:
        user, err = _require_admin(conn)
        if err:
            return err

        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT date, bar_buy, bar_sell, ornament_buy, ornament_sell
                FROM daily_gold_prices
                ORDER BY date DESC
                LIMIT 30
            """)
            rows = cursor.fetchall() or []

        # Serialize dates
        items = []
        for r in rows:
            d = dict(r)
            if hasattr(d.get("date"), "isoformat"):
                d["date"] = d["date"].isoformat()
            items.append(d)

        return jsonify(success=True, items=items)
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, message=str(e)), 500
    finally:
        conn.close()


# ── Alerts ────────────────────────────────────────────────────────────────────
@admin_bp.route("/api/admin/alerts", methods=["GET"])
def admin_alerts():
    conn = get_db_connection()
    try:
        user, err = _require_admin(conn)
        if err:
            return err

        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT a.id, a.gold_type, a.alert_type, a.target_price,
                       a.triggered, a.created_at,
                       u.email, u.name
                FROM price_alerts a
                LEFT JOIN users u ON u.id = a.user_id
                ORDER BY a.created_at DESC
                LIMIT 100
            """)
            rows = cursor.fetchall() or []

        items = []
        for r in rows:
            d = dict(r)
            for k in ("created_at",):
                if hasattr(d.get(k), "isoformat"):
                    d[k] = d[k].isoformat()
            items.append(d)

        return jsonify(success=True, items=items)
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, message=str(e)), 500
    finally:
        conn.close()


# ── Users ─────────────────────────────────────────────────────────────────────
@admin_bp.route("/api/admin/users", methods=["GET"])
def admin_users():
    conn = get_db_connection()
    try:
        user, err = _require_admin(conn)
        if err:
            return err

        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, email, role, is_active, created_at
                FROM users
                ORDER BY created_at DESC
                LIMIT 200
            """)
            rows = cursor.fetchall() or []

        users = []
        for r in rows:
            d = dict(r)
            d.pop("password_hash", None)
            if hasattr(d.get("created_at"), "isoformat"):
                d["created_at"] = d["created_at"].isoformat()
            users.append(d)

        return jsonify(success=True, users=users)
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, message=str(e)), 500
    finally:
        conn.close()


# ── Saved Forecasts ───────────────────────────────────────────────────────────
@admin_bp.route("/api/admin/forecasts", methods=["GET"])
def admin_forecasts():
    conn = get_db_connection()
    try:
        user, err = _require_admin(conn)
        if err:
            return err

        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT f.id, f.target_date, f.max_price, f.min_price,
                       f.trend, f.confidence, f.created_at,
                       u.email, u.name
                FROM saved_forecasts f
                LEFT JOIN users u ON u.id = f.user_id
                ORDER BY f.created_at DESC
                LIMIT 100
            """)
            rows = cursor.fetchall() or []

        items = []
        for r in rows:
            d = dict(r)
            for k in ("target_date", "created_at"):
                if hasattr(d.get(k), "isoformat"):
                    d[k] = d[k].isoformat()
            items.append(d)

        return jsonify(success=True, items=items)
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, items=[], message=str(e)), 200
    finally:
        conn.close()


# ── System Logs ───────────────────────────────────────────────────────────────
@admin_bp.route("/api/admin/logs", methods=["GET"])
def admin_logs():
    conn = get_db_connection()
    try:
        user, err = _require_admin(conn)
        if err:
            return err
    finally:
        conn.close()

    # Try reading Gunicorn / recent logs from DB or memory
    try:
        conn2 = get_db_connection()
        with conn2.cursor() as cursor:
            cursor.execute("""
                SELECT created_at, level, message
                FROM system_logs
                ORDER BY created_at DESC
                LIMIT 200
            """)
            rows = cursor.fetchall() or []
        conn2.close()
        lines = [
            f"[{r.get('created_at','')!s}] [{r.get('level','INFO')}] {r.get('message','')}"
            for r in rows
        ]
        return jsonify(success=True, lines=lines)
    except Exception:
        # system_logs table might not exist — return helpful message
        return jsonify(success=True, lines=["[INFO] system_logs table not found — no logs available yet."])
