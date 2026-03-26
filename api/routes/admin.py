"""routes/admin.py — Admin dashboard endpoints."""
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


@admin_bp.route("/api/admin/stats", methods=["GET"])
def admin_stats():
    conn = get_db_connection()
    try:
        user, err = _require_admin(conn)
        if err: return err

        with conn.cursor() as cursor:
            # Users count
            cursor.execute("SELECT COUNT(*) as c FROM users")
            users_count = cursor.fetchone()["c"]
            
            # Active alerts count
            cursor.execute("SELECT COUNT(*) as c FROM price_alerts WHERE triggered=0")
            alerts_count = cursor.fetchone()["c"]
            
            # Total forecasts count
            try:
                cursor.execute("SELECT COUNT(*) as c FROM saved_forecasts")
                forecasts_count = cursor.fetchone()["c"]
            except Exception:
                forecasts_count = 0

            # Latest gold prices from cache
            from services.gold_price import _thai_gold_cache, _world_gold_cache
            thai = _thai_gold_cache.get("latest", {})
            world = _world_gold_cache.get("latest", {})

        return jsonify(
            success=True,
            data={
                "users_count": users_count,
                "alerts_count": alerts_count,
                "forecasts_count": forecasts_count,
                "thai_gold": thai,
                "world_gold": world
            }
        )
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, message=str(e)), 500
    finally:
        conn.close()


@admin_bp.route("/api/admin/price-history", methods=["GET"])
def admin_price_history():
    conn = get_db_connection()
    try:
        user, err = _require_admin(conn)
        if err: return err

        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM daily_gold_prices ORDER BY date DESC LIMIT 30")
            rows = cursor.fetchall() or []
        
        return jsonify(success=True, items=rows)
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, message=str(e)), 500
    finally:
        conn.close()
