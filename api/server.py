# ===================== server.py =====================
from flask import Flask, jsonify, request, send_from_directory
import time, random, traceback, threading, os, smtplib, hmac, hashlib, base64, re, json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import concurrent.futures
import pymysql
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    import bcrypt
    HAVE_BCRYPT = True
except Exception:
    HAVE_BCRYPT = False

# Load .env from the same directory as server.py
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# --- ไลบรารีเสริม ---
try:
    import yfinance as yf
    HAVE_YFINANCE = True
except ImportError:
    HAVE_YFINANCE = False
try:
    import numpy as np
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import PolynomialFeatures
    HAVE_SKLEARN = True
except ImportError:
    HAVE_SKLEARN = False
try:
    from statsmodels.tsa.arima.model import ARIMA
    HAVE_ARIMA = True
except ImportError:
    HAVE_ARIMA = False
    print("⚠️  statsmodels not installed — ARIMA unavailable, using sklearn fallback")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

app = Flask(__name__)

ALLOWED_ORIGINS = ['http://localhost', 'http://127.0.0.1']

@app.after_request
def after_request(response):
    origin = request.headers.get('Origin', '')
    if any(origin.startswith(o) for o in ALLOWED_ORIGINS):
        response.headers['Access-Control-Allow-Origin'] = origin
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response


@app.route("/", methods=["GET"])
def root():
    return send_from_directory(PROJECT_ROOT, "index.html")


@app.route("/api/meta", methods=["GET"])
def api_meta():
    return jsonify(
        ok=True,
        service="gold-price-checker",
        endpoints=[
            "/api/thai-gold-price",
            "/api/world-gold-price",
            "/api/intraday?range=1d",
            "/api/historical?days=365",
            "/api/forecast?period=7&model=auto&hist_days=90",
            "/api/jobs/run",
            "/webhook",
        ],
    )


@app.route("/health", methods=["GET"])
def health():
    return jsonify(ok=True, time=datetime.now().isoformat())


@app.route("/<path:path>", methods=["GET"])
def static_files(path):
    if path.startswith("api/"):
        return jsonify(ok=False, message="Not Found"), 404
    full_path = os.path.join(PROJECT_ROOT, path)
    if os.path.isfile(full_path):
        return send_from_directory(PROJECT_ROOT, path)
    return send_from_directory(PROJECT_ROOT, "index.html")


def _cookie_secure() -> bool:
    v = (os.getenv("COOKIE_SECURE") or "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    return bool(request.is_secure)


def _bcrypt_verify(password: str, password_hash: str) -> bool:
    if not HAVE_BCRYPT:
        raise RuntimeError("bcrypt is required for password verification")
    if not password_hash:
        return False
    h = password_hash
    if h.startswith("$2y$"):
        h = "$2b$" + h[4:]
    try:
        return bcrypt.checkpw(password.encode("utf-8"), h.encode("utf-8"))
    except Exception:
        return False


def _bcrypt_hash(password: str) -> str:
    if not HAVE_BCRYPT:
        raise RuntimeError("bcrypt is required for password hashing")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


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


@app.route("/api/api/auth/login.php", methods=["POST", "OPTIONS"])
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
                (
                    user["id"],
                    token,
                    expires_at_db,
                    request.headers.get("X-Forwarded-For", request.remote_addr),
                    request.headers.get("User-Agent", "")[:1000],
                ),
            )
        conn.commit()

        resp = jsonify(success=True, message="เข้าสู่ระบบสำเร็จ!", user={k: v for k, v in user.items() if k != "password_hash"})
        resp.set_cookie(
            "session_token",
            token,
            expires=expires_ts,
            path="/",
            secure=_cookie_secure(),
            httponly=True,
            samesite="Lax",
        )
        return resp, 200
    except Exception:
        traceback.print_exc()
        return jsonify(success=False, message="Server error while processing login."), 500
    finally:
        conn.close()


@app.route("/api/api/auth/register.php", methods=["POST", "OPTIONS"])
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


@app.route("/api/api/auth/check_session.php", methods=["POST", "OPTIONS"])
def php_compat_check_session():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200

    token = request.cookies.get("session_token") or ""
    conn = get_db_connection()
    try:
        user = _auth_get_user_by_session(conn, token)
        if user:
            u = {k: v for k, v in user.items() if k != "password_hash"}
            return jsonify(success=True, authenticated=True, user=u), 200
        resp = jsonify(success=True, authenticated=False)
        resp.set_cookie("session_token", "", expires=0, path="/")
        return resp, 200
    except Exception:
        traceback.print_exc()
        return jsonify(success=False, authenticated=False, message="Server error during session check"), 500
    finally:
        conn.close()


@app.route("/api/api/auth/logout.php", methods=["POST", "OPTIONS"])
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


@app.route("/api/web-push/public-key", methods=["GET"])
def web_push_public_key():
    key = (os.getenv("VAPID_PUBLIC_KEY") or "").strip()
    return jsonify(success=True, public_key=key), 200


@app.route("/api/api/profile/update_push.php", methods=["POST", "OPTIONS"])
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

        try:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE users SET push_subscription=%s WHERE id=%s", (sub_str, user["id"]))
            conn.commit()
        except Exception as e:
            conn.rollback()
            return jsonify(success=False, message=str(e)), 500

        return jsonify(success=True, message="Subscription updated"), 200
    finally:
        conn.close()


def _require_auth_user(conn):
    token = request.cookies.get("session_token") or ""
    user = _auth_get_user_by_session(conn, token)
    if not user:
        return None, (jsonify(success=False, message="กรุณาเข้าสู่ระบบ"), 401)
    return user, None


@app.route("/api/api/profile/generate_line_code.php", methods=["POST", "OPTIONS"])
def php_compat_generate_line_code():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200

    conn = get_db_connection()
    try:
        user, err = _require_auth_user(conn)
        if err:
            return err

        code = str(random.randint(0, 999999)).zfill(6)
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET verification_token=%s WHERE id=%s", (code, user["id"]))
        conn.commit()
        return jsonify(success=True, code=code, message="Code generated successfully"), 200
    except Exception:
        traceback.print_exc()
        return jsonify(success=False, message="Server Error"), 500
    finally:
        conn.close()


@app.route("/api/api/profile/update_line.php", methods=["POST", "OPTIONS"])
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

        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET line_user_id=%s, line_display_name=%s WHERE id=%s",
                (line_id, display_name, user["id"]),
            )
        conn.commit()
        return jsonify(success=True, message="เชื่อมต่อ LINE สำเร็จ"), 200
    except Exception:
        traceback.print_exc()
        return jsonify(success=False, message="Server Error"), 500
    finally:
        conn.close()


@app.route("/api/api/alerts/create.php", methods=["POST", "OPTIONS"])
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
                    """
                    INSERT INTO price_alerts (user_id, target_price, alert_type, gold_type, notify_email, channel_email, triggered)
                    VALUES (%s, %s, %s, %s, %s, 1, 0)
                    """,
                    (user["id"], target_price, alert_type, gold_type, email or user.get("email")),
                )
            except Exception:
                cursor.execute(
                    """
                    INSERT INTO price_alerts (user_id, target_price, alert_type, gold_type, email, triggered)
                    VALUES (%s, %s, %s, %s, %s, 0)
                    """,
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


@app.route("/api/api/alerts/list.php", methods=["GET", "OPTIONS"])
def php_compat_alerts_list():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200

    conn = get_db_connection()
    try:
        user, err = _require_auth_user(conn)
        if err:
            return err

        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM price_alerts WHERE user_id=%s ORDER BY created_at DESC",
                (user["id"],),
            )
            items = cursor.fetchall() or []
        return jsonify(success=True, items=items), 200
    except Exception:
        traceback.print_exc()
        return jsonify(success=False, message="โหลดไม่สำเร็จ"), 500
    finally:
        conn.close()


@app.route("/api/api/alerts/delete.php", methods=["POST", "OPTIONS"])
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


@app.route("/api/api/user/save_forecast.php", methods=["POST", "OPTIONS"])
def php_compat_save_forecast():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200

    data = request.get_json(silent=True) or {}
    target_date = (data.get("target_date") or "")[:10]
    trend = (data.get("trend") or "").strip()
    max_price = data.get("max_price")
    min_price = data.get("min_price")
    confidence = data.get("confidence")
    hist_days = data.get("hist_days")

    try:
        max_price = float(max_price)
        min_price = float(min_price)
        confidence = float(confidence)
        hist_days = int(hist_days)
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
                """
                INSERT INTO saved_forecasts (user_id, forecast_date, target_date, trend, max_price, min_price, confidence, hist_days)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (user["id"], forecast_date, target_date, trend, max_price, min_price, confidence, hist_days),
            )
        conn.commit()
        return jsonify(success=True, message="บันทึกสำเร็จ!"), 200
    except Exception:
        traceback.print_exc()
        return jsonify(success=False, message="บันทึกไม่สำเร็จ"), 500
    finally:
        conn.close()


@app.route("/api/api/user/get_saved_forecasts.php", methods=["GET", "OPTIONS"])
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
                    """
                    SELECT id, user_id, forecast_date, target_date, trend, max_price, min_price, confidence, hist_days,
                           actual_max_price, actual_min_price, verified_at, created_at
                    FROM saved_forecasts
                    WHERE user_id=%s
                    ORDER BY created_at DESC
                    LIMIT 100
                    """,
                    (user["id"],),
                )
            except Exception:
                cursor.execute(
                    """
                    SELECT *
                    FROM saved_forecasts
                    WHERE user_id=%s
                    ORDER BY created_at DESC
                    LIMIT 100
                    """,
                    (user["id"],),
                )
            rows = cursor.fetchall() or []
        return jsonify(success=True, data=rows), 200
    except Exception:
        traceback.print_exc()
        return jsonify(success=False, message="โหลดไม่สำเร็จ"), 500
    finally:
        conn.close()


@app.route("/api/api/notifications/list.php", methods=["GET", "OPTIONS"])
def php_compat_notifications_list():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200

    conn = get_db_connection()
    try:
        user, err = _require_auth_user(conn)
        if err:
            return err

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, title, message, type, is_read, link, created_at
                FROM notifications
                WHERE user_id=%s
                ORDER BY created_at DESC
                LIMIT 20
                """,
                (user["id"],),
            )
            items = cursor.fetchall() or []
            cursor.execute("SELECT COUNT(*) AS c FROM notifications WHERE user_id=%s AND is_read=0", (user["id"],))
            unread = cursor.fetchone() or {"c": 0}
        return jsonify(success=True, data=items, unread_count=int(unread.get("c") or 0)), 200
    except Exception:
        traceback.print_exc()
        return jsonify(success=False, message="โหลดไม่สำเร็จ"), 500
    finally:
        conn.close()


@app.route("/api/api/notifications/mark_read.php", methods=["POST", "OPTIONS"])
def php_compat_notifications_mark_read():
    if request.method == "OPTIONS":
        return jsonify(success=True), 200

    data = request.get_json(silent=True) or {}
    notif_id = data.get("id")

    conn = get_db_connection()
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
        return jsonify(success=False, message="Server Error"), 500
    finally:
        conn.close()

# --- CONFIG (from .env) ---
CONFIG = {
    "ALPHA_VANTAGE_KEY": os.getenv("ALPHA_VANTAGE_KEY", ""),
    "NEWSAPI_KEY": os.getenv("NEWSAPI_KEY", "")
}

# --- Cache --- 
CACHE_DURATION = 30
thai_cache  = {"data": None, "ts": 0}
world_cache = {"data": None, "ts": 0}
historical_cache = {"data": None, "ts": 0, "date": None}

# -------------------- Database Utility --------------------
def get_db_connection():
    host = os.getenv("DB_HOST")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASS")
    database = os.getenv("DB_NAME")
    port = int(os.getenv("DB_PORT", 3306))

    print("DB_HOST:", host)
    print("DB_USER:", user)
    print("DB_NAME:", database)
    print("DB_PORT:", port)

    return pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port,
        cursorclass=pymysql.cursors.DictCursor
    )

# -------------------- ยูทิลิตี้และตัวดึงข้อมูล --------------------
def to_float(x):
    try: return float(str(x).replace(",", "").strip())
    except Exception: return None

def normalize_prices(d: dict): # ทำความสะอาดข้อมูลราคา
    for k in ("bar_buy","bar_sell","ornament_buy","ornament_sell", "today_change"):
        if k in d and d[k] is not None: d[k] = to_float(d[k])
    if d.get("bar_buy") and d.get("bar_sell") and d["bar_buy"] > d["bar_sell"]:
        d["bar_buy"], d["bar_sell"] = d["bar_sell"], d["bar_buy"]
    if d.get("ornament_buy") and d.get("ornament_sell") and d["ornament_buy"] > d["ornament_sell"]:
        d["ornament_buy"], d["ornament_sell"] = d["ornament_sell"], d["ornament_buy"]
    return d

def get_usdthb(): # ดึงค่าอัตราแลกเปลี่ยน USDTHB
    try:
        r = requests.get("https://api.exchangerate.host/latest", params={"base":"USD","symbols":"THB"}, timeout=10)
        r.raise_for_status(); return float(r.json()["rates"]["THB"])
    except Exception: return 36.85

WORLD_PRICE_MIN = 500.0
WORLD_PRICE_MAX = 10000.0
HTTP_HEADERS = {"User-Agent": "Mozilla/5.0"}


def _is_valid_world_price(value):
    v = to_float(value)
    return v is not None and WORLD_PRICE_MIN <= v <= WORLD_PRICE_MAX


def _fetch_world_from_goldprice_org():
    r = requests.get(
        "https://data-asg.goldprice.org/dbXRates/USD",
        timeout=10,
        headers=HTTP_HEADERS,
    )
    r.raise_for_status()
    payload = r.json()
    price = to_float(payload.get("items", [{}])[0].get("xauPrice"))
    if not _is_valid_world_price(price):
        raise ValueError(f"goldprice.org returned invalid xauPrice: {price}")
    return float(price)


def _parse_metals_live_payload(payload):
    if isinstance(payload, list) and payload:
        row = payload[-1]
        if isinstance(row, (list, tuple)) and row:
            # รูปแบบที่พบบ่อย: [timestamp, gold, silver, ...] หรือ [timestamp, gold]
            if len(row) >= 2 and _is_valid_world_price(row[1]):
                return float(row[1])
            if _is_valid_world_price(row[0]):
                return float(row[0])
        if isinstance(row, dict):
            for key in ("gold", "price", "xau", "xauusd"):
                if _is_valid_world_price(row.get(key)):
                    return float(row[key])
        if _is_valid_world_price(row):
            return float(row)
    if isinstance(payload, dict):
        for key in ("gold", "price", "xau", "xauusd"):
            if _is_valid_world_price(payload.get(key)):
                return float(payload[key])
    raise ValueError("metals.live payload format not recognized")


def _fetch_world_from_metals_live():
    endpoints = [
        "https://api.metals.live/v1/spot/gold",
        "https://api.metals.live/v1/spot",
    ]
    last_error = None
    for url in endpoints:
        try:
            r = requests.get(url, timeout=10, headers=HTTP_HEADERS)
            r.raise_for_status()
            return _parse_metals_live_payload(r.json())
        except Exception as e:
            last_error = e
    if last_error:
        raise last_error
    raise ValueError("metals.live source failed")


def _fetch_world_from_stooq():
    r = requests.get("https://stooq.com/q/l/?s=xauusd&i=d", timeout=10, headers=HTTP_HEADERS)
    r.raise_for_status()
    lines = [line.strip() for line in r.text.splitlines() if line.strip()]
    if len(lines) < 2:
        raise ValueError("stooq returned no CSV rows")

    headers = [h.strip().lower() for h in lines[0].split(",")]
    values = [v.strip() for v in lines[1].split(",")]
    row = dict(zip(headers, values))
    close = to_float(row.get("close"))
    if close is None and len(values) >= 7:
        close = to_float(values[6])
    if not _is_valid_world_price(close):
        raise ValueError(f"stooq close invalid: {close}")
    return float(close)


def _fetch_world_from_fred_lbma():
    r = requests.get(
        "https://fred.stlouisfed.org/graph/fredgraph.csv?id=GOLDAMGBD228NLBM",
        timeout=10,
        headers=HTTP_HEADERS,
    )
    r.raise_for_status()
    lines = [line.strip() for line in r.text.splitlines() if line.strip()]
    if len(lines) < 2:
        raise ValueError("FRED returned no data")

    for line in reversed(lines[1:]):
        parts = line.split(",")
        if len(parts) < 2:
            continue
        if parts[1].strip() in ("", "."):
            continue
        price = to_float(parts[1])
        if _is_valid_world_price(price):
            return float(price)
    raise ValueError("FRED has no valid latest world gold value")


def _fetch_world_from_yfinance():
    if not HAVE_YFINANCE:
        raise ImportError("yfinance not installed")
    for symbol in ("XAUUSD=X", "GC=F"):
        try:
            t = yf.Ticker(symbol)
            # Fetch a slightly longer period to prevent empty DataFrames on holidays/weekends
            hist = t.history(period="5d")
            if hist is not None and not hist.empty and len(hist) > 0:
                price = to_float(hist["Close"].iloc[-1])
                if _is_valid_world_price(price):
                    return float(price)
        except Exception:
            continue
    raise ValueError("Yahoo Finance symbols returned no valid price")


WORLD_SPOT_SOURCES = [
    ("Yahoo Finance", "XAUUSD=X / GC=F", _fetch_world_from_yfinance),
    ("Metals.Live", "https://api.metals.live/v1/spot/gold", _fetch_world_from_metals_live),
    ("GoldPrice.org", "https://data-asg.goldprice.org/dbXRates/USD", _fetch_world_from_goldprice_org),
    ("Stooq", "https://stooq.com/q/l/?s=xauusd&i=d", _fetch_world_from_stooq),
    ("FRED LBMA AM", "https://fred.stlouisfed.org/graph/fredgraph.csv?id=GOLDAMGBD228NLBM", _fetch_world_from_fred_lbma),
]

def get_world_spot_usd_per_oz(): # ดึงราคาทองคำตลาดโลก (Spot Price) เป็น USD ต่อทรอยออนซ์
    errors = []
    
    def fetch_source(source_info):
        source_name, source_url, fetcher = source_info
        try:
            price = to_float(fetcher())
            if _is_valid_world_price(price):
                return float(price), source_name, source_url
            raise ValueError(f"invalid price: {price}")
        except Exception as e:
            errors.append(f"{source_name}: {e}")
            raise # Re-raise to track failed futures

    # Use ThreadPoolExecutor to run all sources concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(WORLD_SPOT_SOURCES)) as executor:
        # Map futures to source names for error tracking
        future_to_source = {executor.submit(fetch_source, source): source[0] for source in WORLD_SPOT_SOURCES}
        
        # Return the FIRST successful result immediately
        for future in concurrent.futures.as_completed(future_to_source):
            try:
                result = future.result()
                if result:
                    print(f"World source success (Fastest): {result[1]} -> {result[0]}")
                    # Cancel pending futures (Python 3.9+) if possible, though context manager handles exit
                    return result
            except Exception:
                pass # Exceptions already caught and appended to errors list
                
    raise RuntimeError("All world sources failed: " + " | ".join(errors))

def usd_oz_to_thb_per_baht(usd, usdthb): # แปลง USD ต่อทรอยออนซ์ เป็น บาทต่อบาททองคำ (96.5% บริสุทธิ์)
    return usd * (15.244 / 31.1035) * usdthb

# -------------------- สแครปเปอร์ (อัปเดตทั้งหมด) --------------------

def scrape_from_finnomena(): # Finnomena API
    print("Attempting to fetch from finnomena.com API...")
    url = "https://www.finnomena.com/fn-service/api/v2/gold/YLG"
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.finnomena.com/gold'}
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()['data']
    result = {
        "bar_buy": data['goldBar']['bid'], "bar_sell": data['goldBar']['ask'],
        "ornament_buy": data['ornament']['bid'], "ornament_sell": data['ornament']['ask'],
        "today_change": data['goldBar']['change'], "date": data['updatedAt'].split('T')[0],
        "source_note": "Finnomena API",
    }
    print("Success from finnomena.com API.")
    return normalize_prices(result)

def scrape_from_goldprice_or_th(): # goldprice.or.th API
    print("Attempting to fetch from goldprice.or.th API...")
    url = "https://www.goldprice.or.th/api/latest_price"
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
    r.raise_for_status()
    payload = r.json()

    def pick(row, keys):
        for key in keys:
            if isinstance(row, dict) and key in row and row.get(key) not in (None, ""):
                return row.get(key)
        return None

    candidate_rows = []
    if isinstance(payload, dict):
        if isinstance(payload.get("results"), list):
            candidate_rows.extend([x for x in payload["results"] if isinstance(x, dict)])
        if isinstance(payload.get("data"), list):
            candidate_rows.extend([x for x in payload["data"] if isinstance(x, dict)])
        if isinstance(payload.get("data"), dict):
            candidate_rows.append(payload["data"])
        if isinstance(payload.get("response"), dict):
            candidate_rows.append(payload["response"])
        candidate_rows.append(payload)
    elif isinstance(payload, list):
        candidate_rows.extend([x for x in payload if isinstance(x, dict)])

    for row in candidate_rows:
        data = {
            "bar_buy": pick(row, ("buy_bar", "bar_buy", "gold_bar_buy", "bid", "bid_bar")),
            "bar_sell": pick(row, ("sell_bar", "bar_sell", "gold_bar_sell", "ask", "ask_bar")),
            "ornament_buy": pick(row, ("buy_ornament", "ornament_buy", "jewelry_buy", "buy_jewelry")),
            "ornament_sell": pick(row, ("sell_ornament", "ornament_sell", "jewelry_sell", "sell_jewelry")),
            "today_change": pick(row, ("price_change", "today_change", "change")),
            "date": pick(row, ("date", "price_date", "updated_date")) or datetime.now().strftime("%Y-%m-%d"),
            "source_note": "goldprice.or.th API",
        }
        normalized = normalize_prices(data)
        required = ("bar_buy", "bar_sell", "ornament_buy", "ornament_sell")
        if all(normalized.get(k) is not None for k in required):
            print("Success from goldprice.or.th API.")
            return normalized

    raise ValueError("goldprice.or.th payload format changed or incomplete")

def scrape_from_gta():# Gold Traders Association
    print("Attempting to fetch from goldtraders.or.th (HTML)...")
    url = "https://www.goldtraders.or.th/"
    r = requests.get(url, timeout=15, headers={"User-Agent":"Mozilla/5.0"})
    r.raise_for_status()
    import re
    html = r.text
    
    def extract_val(pattern):
        match = re.search(pattern, html)
        if match:
            # Strip tags and clean out commas
            clean = re.sub(r'<[^>]+>', '', match.group(1)).replace(',', '').strip()
            return clean if clean else None
        return None

    # New HTML structure extraction using Regex as BeautifulSoup fallback
    bar_sell = extract_val(r'<span\s+id="DetailPlace_uc_goldprices1_lblBLSell"[^>]*>(.*?)</span>')
    bar_buy = extract_val(r'<span\s+id="DetailPlace_uc_goldprices1_lblBLBuy"[^>]*>(.*?)</span>')
    ornament_sell = extract_val(r'<span\s+id="DetailPlace_uc_goldprices1_lblOMSell"[^>]*>(.*?)</span>')
    ornament_buy = extract_val(r'<span\s+id="DetailPlace_uc_goldprices1_lblOMBuy"[^>]*>(.*?)</span>')
    today_change = extract_val(r'<span\s+id="DetailPlace_uc_goldprices1_lblDayChange"[^>]*>(.*?)</span>')
    update_text = extract_val(r'<span\s+id="DetailPlace_uc_goldprices1_lblDate"[^>]*>(.*?)</span>')
    
    if not (bar_sell and bar_buy and ornament_sell and ornament_buy):
        raise ValueError("Price values not found on GTA with new regex structure.")

    update_round = ""
    if update_text:
        round_match = re.search(r'ครั้งที่\s*(\d+)', update_text)
        if round_match:
            update_round = round_match.group(1)

    # Some numbers have + or - in today change
    if today_change:
        today_change = today_change.replace('+', '').strip()

    data = {
        "bar_buy": bar_buy,
        "bar_sell": bar_sell,
        "ornament_buy": ornament_buy,
        "ornament_sell": ornament_sell,
        "today_change": today_change or "0",
        "update_round": update_round or "ล่าสุด",
        "date": datetime.now().strftime("%Y-%m-%d"), "source_note": "GTA (Regex)",
    }
    print(f"Success from goldtraders.or.th (Regex HTML). Round: {update_round}, Change: {today_change}")
    return normalize_prices(data)

def scrape_from_thongkam(): #` Thongkam Gold`
    print("Attempting to fetch from thongkam.com...")
    url = "https://xn--42cah7d0cxcvbbb9x.com/"
    r = requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    div = soup.find("div", id="divDaily")
    if not div: raise ValueError("divDaily not found")
    tds = div.select("td")
    # td[4]=ทองคำแท่ง 96.5%, td[5]=ราคาขาย, td[6]=ราคารับซื้อ
    # td[8]=ทองรูปพรรณ 96.5%, td[9]=ราคาขาย, td[10]=ราคารับซื้อ
    data = {
        "bar_sell": tds[5].get_text(strip=True),
        "bar_buy": tds[6].get_text(strip=True),
        "ornament_sell": tds[9].get_text(strip=True),
        "ornament_buy": tds[10].get_text(strip=True),
        "source_note": "Thongkam.com",
    }
    
    # ดึงครั้งที่อัพเดทและราคาเปลี่ยนแปลงจากหน้าเว็บ
    import re
    try:
        page_text = soup.get_text()
        # ดึงครั้งที่อัพเดท เช่น "(ครั้งที่ 15)"
        round_match = re.search(r'\(ครั้งที่\s*(\d+)\)', page_text)
        if round_match:
            data["update_round"] = round_match.group(1)
        # ดึงราคาเปลี่ยนแปลง เช่น "วันนี้ขึ้น100" หรือ "วันนี้ลง100"
        change_match = re.search(r'วันนี้(ขึ้น|ลง)(\d[\d,]*)', page_text)
        if change_match:
            direction = change_match.group(1)
            amount = change_match.group(2).replace(',', '')
            data["today_change"] = int(amount) if direction == 'ขึ้น' else -int(amount)
    except Exception as e:
        print(f"Could not extract round/change from thongkam: {e}") 
    
    print(f"Success from thongkam.com. Data: {data}")
    return normalize_prices(data)

def scrape_from_intergold():
    print("Attempting to fetch from intergold.co.th (AJAX)...")
    url = "https://www.intergold.co.th/wp-admin/admin-ajax.php"
    payload = {
        "action": "ajaxGetPriceApi",
        "type": "hour",
        "page": "1",
        "limit": "1",
    }
    r = requests.post(url, data=payload, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    body = r.json()
    html_rows = body.get("html")
    if not html_rows:
        raise ValueError("Intergold returned empty html payload")

    soup = BeautifulSoup(f"<table>{html_rows}</table>", "lxml")
    first_row = soup.find("tr")
    if not first_row:
        raise ValueError("Intergold returned no table row")

    cells = [td.get_text(strip=True) for td in first_row.find_all("td")]
    # โครงสร้างที่คาด: [datetime, lbma_buy, lbma_sell, intergold_buy, intergold_sell, gta_buy, gta_sell, spot, usdthb]
    if len(cells) < 7:
        raise ValueError(f"Intergold row incomplete: {cells}")

    date_text = cells[0] if cells else ""
    date_value = datetime.now().strftime("%Y-%m-%d")
    try:
        date_value = datetime.strptime(date_text.split()[0], "%d/%m/%Y").strftime("%Y-%m-%d")
    except Exception:
        pass

    data = {
        # สมาคมฯ 96.5% จาก Intergold feed
        "bar_buy": cells[5],
        "bar_sell": cells[6],
        # ใช้ราคา Intergold 96.5% เป็นค่ารูปพรรณ fallback เมื่อแหล่งหลักล่ม
        "ornament_buy": cells[3],
        "ornament_sell": cells[4],
        "date": date_value,
        "source_note": "Intergold (AJAX)",
    }

    print(f"Success from intergold.co.th (AJAX). Data: {data}")
    return normalize_prices(data)

def scrape_from_huasengheng():
    print("Attempting to fetch from huasengheng.com API...")
    url = "https://www.huasengheng.com/wp-admin/admin-ajax.php"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.huasengheng.com/",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    try:
        r = requests.post(url, data={"action": "get_gold_price"}, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data or not isinstance(data, dict):
            raise ValueError("Hua Seng Heng returned unexpected payload")

        price_data = {
            "bar_buy": data.get("buy965"),
            "bar_sell": data.get("sell965"),
            "ornament_buy": data.get("buy965_ornament", data.get("buy965")),
            "ornament_sell": data.get("sell965_ornament", data.get("sell965")),
            "today_change": data.get("change965"),
            "source_note": "HuaSengHeng (API)",
        }
        print("Success from Hua Seng Heng.")
        return normalize_prices(price_data)
    except Exception as e:
         print(f"Hua Seng Heng fetch failed: {e}")
         raise

def scrape_from_ecg(): # ECG Goldshop
    print("Attempting to fetch from ecggoldshop.com...")
    url = "https://ecggoldshop.com/calculate/"
    r = requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    data = { 
        "bar_buy": soup.find("input", {"id": "bar_buy"})["value"], 
        "bar_sell": soup.find("input", {"id": "bar_sell"})["value"], 
        "ornament_buy": soup.find("input", {"id": "jiw_sell"})["value"], 
        "ornament_sell": soup.find("input", {"id": "jiw_buy"})["value"], 
        "source_note": "ECG" 
    }
    print("Success from ecggoldshop.com.")
    return normalize_prices(data)

# -------------------- API ราคาสด --------------------
def refresh_world_cache(force=False):
    now = time.time()
    if not force and world_cache.get("data") and now - world_cache.get("ts", 0) < CACHE_DURATION:
        return world_cache["data"]

    usd_per_oz, source_note, source_url = get_world_spot_usd_per_oz()
    usdthb = get_usdthb()
    thb_per_baht = usd_oz_to_thb_per_baht(usd_per_oz, usdthb)
    data = {
        "price_usd_per_ounce": round(usd_per_oz, 2),
        "usdthb": round(usdthb, 4),
        "thb_per_baht_est": round(thb_per_baht, 2),
        "last_updated": datetime.now().strftime("%H:%M:%S"),
        "source_note": source_note,
        "source_url": source_url,
    }
    world_cache.update({"data": data, "ts": now})
    return data


def refresh_thai_cache(force=False):
    now = time.time()

    prev_bar_sell = None
    if thai_cache.get("data") and thai_cache["data"].get("bar_sell") is not None:
        try:
            prev_bar_sell = float(thai_cache["data"]["bar_sell"])
        except Exception:
            prev_bar_sell = None

    if not force and thai_cache.get("data") and now - thai_cache.get("ts", 0) < CACHE_DURATION:
        return thai_cache["data"]

    scrapers = [
        scrape_from_gta,
        scrape_from_thongkam,
        scrape_from_goldprice_or_th,
        scrape_from_huasengheng,
        scrape_from_intergold,
        scrape_from_finnomena,
        scrape_from_ecg,
    ]

    def run_scraper(fn):
        data = fn()
        if not all(data.get(k) is not None for k in ("bar_buy", "bar_sell", "ornament_buy", "ornament_sell")):
            raise ValueError("Incomplete data")
        if not data.get("date"):
            data["date"] = datetime.now().strftime("%Y-%m-%d")
        if not data.get("update_round"):
            data["update_round"] = data.get("round") or "ล่าสุด"
        if data.get("today_change") is None:
            if prev_bar_sell is not None and data.get("bar_sell") is not None:
                data["today_change"] = float(data["bar_sell"]) - prev_bar_sell
            else:
                data["today_change"] = 0
        return data

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(scrapers)) as executor:
        future_to_fn = {executor.submit(run_scraper, fn): fn.__name__ for fn in scrapers}
        for future in concurrent.futures.as_completed(future_to_fn):
            try:
                data = future.result()
                thai_cache.update({"data": data, "ts": now})
                return data
            except Exception:
                pass

    if thai_cache.get("data"):
        stale = dict(thai_cache["data"])
        stale["stale"] = True
        return stale

    raise ValueError("All scrapers failed")


@app.route("/api/world-gold-price")
def api_world():
    try:
        data = refresh_world_cache()
        return jsonify(data)
    except Exception as e:
        print(f"WORLD PRICE ERROR: {e}"); traceback.print_exc()
        if world_cache.get("data"):
            stale = dict(world_cache["data"])
            stale["stale"] = True
            return jsonify(stale), 200
        # Fallback สำรอง: ประมาณ Spot โลกจากราคาทองไทยล่าสุด
        # สูตรย้อนกลับจากบาท/บาททอง -> USD/Oz
        try:
            thai_data = thai_cache.get("data") or {}
            thai_bar_sell = to_float(thai_data.get("bar_sell"))
            usdthb = get_usdthb()
            factor = (15.244 / 31.1035) * usdthb
            if thai_bar_sell and factor > 0:
                usd_per_oz_est = thai_bar_sell / factor
                data = {
                    "price_usd_per_ounce": round(usd_per_oz_est, 2),
                    "usdthb": round(usdthb, 4),
                    "thb_per_baht_est": round(thai_bar_sell, 2),
                    "last_updated": datetime.now().strftime("%H:%M:%S"),
                    "estimated": True,
                    "source_note": "Estimated from Thai bar sell",
                    "source_url": "derived://thai-bar-sell",
                }
                world_cache.update({"data": data, "ts": time.time()})
                return jsonify(data), 200
        except Exception:
            pass
        return jsonify({"error": "Failed to fetch world gold price"}), 500

@app.route("/api/thai-gold-price")
def api_thai():
    try:
        data = refresh_thai_cache()
        try:
            threading.Thread(target=save_daily_price, daemon=True).start()
        except Exception:
            pass
        return jsonify(data)
    except Exception as e:
        print(f"FATAL ERROR in api_thai: {e}"); traceback.print_exc()
        return jsonify({"error": "Internal Server Error in Thai Price API"}), 500
# -------------------- Daily Price Cache --------------------
def save_daily_price():
    """Save today's Thai gold price to price_cache table (runs once per day)."""
    try:
        thai_data = thai_cache.get("data")
        world_data = world_cache.get("data")
        if not thai_data or not thai_data.get("bar_sell"):
            return

        today = datetime.now().date()
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Check if today's price already exists
                cursor.execute("SELECT id FROM price_cache WHERE date=%s", (today,))
                if cursor.fetchone():
                    # Update existing record
                    cursor.execute("""
                        UPDATE price_cache SET
                            bar_buy=%s, bar_sell=%s, ornament_buy=%s, ornament_sell=%s,
                            world_usd=%s, world_thb=%s
                        WHERE date=%s
                    """, (
                        to_float(thai_data.get('bar_buy')),
                        to_float(thai_data.get('bar_sell')),
                        to_float(thai_data.get('ornament_buy')),
                        to_float(thai_data.get('ornament_sell')),
                        to_float(world_data.get('price_usd_per_ounce')) if world_data else None,
                        to_float(world_data.get('thb_per_baht_est')) if world_data else None,
                        today
                    ))
                else:
                    cursor.execute("""
                        INSERT INTO price_cache (date, bar_buy, bar_sell, ornament_buy, ornament_sell, world_usd, world_thb)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        today,
                        to_float(thai_data.get('bar_buy')),
                        to_float(thai_data.get('bar_sell')),
                        to_float(thai_data.get('ornament_buy')),
                        to_float(thai_data.get('ornament_sell')),
                        to_float(world_data.get('price_usd_per_ounce')) if world_data else None,
                        to_float(world_data.get('thb_per_baht_est')) if world_data else None
                    ))
            conn.commit()
            print(f"✅ Saved daily price to cache: {today} bar_sell={thai_data.get('bar_sell')}")
        finally:
            conn.close()
    except Exception as e:
        print(f"⚠️ Failed to save daily price: {e}")


def build_series_from_db(days=365):
    """Load historical Thai gold prices from price_cache table (REAL data)."""
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT date, bar_sell FROM price_cache
                    WHERE bar_sell IS NOT NULL
                    ORDER BY date ASC
                    LIMIT %s
                """, (days,))
                rows = cursor.fetchall()

            if len(rows) < 10:
                return None, None  # Not enough data

            labels = [r['date'].strftime('%Y-%m-%d') if hasattr(r['date'], 'strftime') else str(r['date']) for r in rows]
            values = [float(r['bar_sell']) for r in rows]
            print(f"✅ Loaded {len(rows)} days of REAL Thai gold data from price_cache")
            return labels, values
        finally:
            conn.close()
    except Exception as e:
        print(f"⚠️ Failed to load from price_cache: {e}")
        return None, None


# -------------------- ตัวดึงข้อมูลประวัติ --------------------
def build_series_from_yfinance(days=365):
    """
    ดึงข้อมูลราคาทอง (GLD) ย้อนหลังจาก Yahoo Finance และแปลงเป็นราคาบาท
    (Fallback — ใช้เมื่อ price_cache ไม่มีข้อมูลพอ)
    """
    if not HAVE_YFINANCE:
        raise ImportError("yfinance library is not installed.")

    print("Attempting to fetch historical data from Yahoo Finance...")
    gld = yf.Ticker("GLD")
    hist = gld.history(period=f"{days + 35}d")

    if hist.empty:
        raise ValueError("Yahoo Finance returned no data for GLD.")

    hist = hist.tail(days)

    labels = [d.strftime('%Y-%m-%d') for d in hist.index]
    values_usd = [v * 10.0 for v in hist['Close']]

    # แปลงเป็นราคาบาท
    usdthb = get_usdthb()
    factor = usdthb * (15.244 / 31.1035)
    values_thb = [v * factor for v in values_usd]

    # ปรับสเกลให้ตรงกับราคาล่าสุด (ถ้ามี)
    try:
        if thai_cache["data"] and thai_cache["data"].get("bar_sell"):
            last_th_real = float(thai_cache["data"]["bar_sell"])
            last_th_calc = values_thb[-1]
            basis = last_th_real - last_th_calc
            values_thb = [v + basis for v in values_thb]
    except Exception as e:
        print(f"Could not adjust yfinance data to Thai price: {e}")

    print("Successfully fetched from Yahoo Finance (adjusted to Thai price).")
    return labels, values_thb

def build_series_with_world_from_yfinance(days=365):
    """Build both Thai and world series. Uses price_cache first, then yfinance fallback."""
    # Try DB first
    db_labels, db_values = build_series_from_db(days)
    if db_labels and db_values and len(db_values) >= 30:
        # For world values, estimate from Thai price
        usdthb = get_usdthb()
        factor = usdthb * (15.244 / 31.1035) * 0.965
        values_usd = [v / factor * 10.0 for v in db_values]  # reverse-estimate USD
        return db_labels, db_values, values_usd

    # Fallback to yfinance
    if not HAVE_YFINANCE:
        raise ImportError("yfinance library is not installed.")

    gld = yf.Ticker("GLD")
    hist = gld.history(period=f"{int(days * 1.5)}d")
    if hist.empty:
        raise ValueError("Yahoo Finance returned no data for GLD.")

    hist = hist.tail(days)
    labels = [d.strftime('%Y-%m-%d') for d in hist.index]
    values_usd = [v * 10.0 for v in hist['Close']]

    usdthb = get_usdthb()
    factor = usdthb * (15.244 / 31.1035) * 0.965
    values_thb = [v * factor for v in values_usd]

    # Adjust to real Thai price
    try:
        if thai_cache["data"] and thai_cache["data"].get("bar_sell"):
            last_th_real = float(thai_cache["data"]["bar_sell"])
            basis = last_th_real - values_thb[-1]
            values_thb = [v + basis for v in values_thb]
    except Exception:
        pass

    return labels, values_thb, values_usd



historical_cache = {"data": None, "ts": 0, "date": None}

def build_historical_gold_data_free(days=365):
    """
    Build historical gold data. Priority:
    1. price_cache DB (real data)
    2. Synthetic data anchored to REAL current Thai price
    """
    # Try DB first
    db_labels, db_values = build_series_from_db(days)
    if db_labels and db_values:
        return db_labels, db_values

    # Fallback: generate synthetic data BUT anchored to real Thai price
    current_thb = 41500.0  # Default fallback

    try:
        if thai_cache["data"] and thai_cache["data"].get("bar_sell"):
            current_thb = float(thai_cache["data"]["bar_sell"])
            print(f"Using real Thai market price for synthetic data: {current_thb}")
    except Exception as e:
        print(f"Could not get Thai price, using fallback: {e}")

        try:
            r = requests.get(
                "https://data-asg.goldprice.org/dbXRates/USD",
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            r.raise_for_status()
            data = r.json()
            usd_per_oz = float(data["items"][0]["xauPrice"])
            usdthb = get_usdthb()

            G_PER_BAHT = 15.244
            G_PER_TROY_OZ = 31.1035
            PURITY = 0.965
            current_thb = usd_per_oz * (G_PER_BAHT / G_PER_TROY_OZ) * usdthb * PURITY
            print(f"Calculated from world spot: {current_thb}")
        except:
            pass

    labels, values = [], []

    random.seed(42)

    price = current_thb * 0.88
    daily_volatility = current_thb * 0.006

    for i in range(days):
        day = (datetime.now().date() - timedelta(days=days-1-i)).isoformat()

        days_remaining = days - i
        mean_reversion = (current_thb - price) / days_remaining * 0.8 if days_remaining > 0 else 0
        random_shock = random.gauss(0, daily_volatility)
        drift = mean_reversion + random_shock

        price = max(current_thb * 0.75, min(current_thb * 1.05, price + drift))

        labels.append(day)
        values.append(round(price, 2))

    if values:
        values[-1] = round(current_thb, 2)

    print(f"Generated {len(values)} days of synthetic data, ending at {values[-1]} baht")

    return labels, values

@app.route("/api/historical")
def api_historical():
    try:
        days = int(request.args.get("days", 365))
        days = max(30, min(days, 365))
        now = time.time()
        today = datetime.now().date().isoformat()
        if (historical_cache["data"] and historical_cache.get("date") == today and now - historical_cache["ts"] < CACHE_DURATION):
            return jsonify(historical_cache["data"])
        source = ""
        try:
            labels, thai_values, world_values = build_series_with_world_from_yfinance(days=days)
            source = "Yahoo Finance"
        except Exception:
            labels, thai_values = build_historical_gold_data_free(days=days)
            usdthb = get_usdthb()
            factor = usdthb * (15.244 / 31.1035)
            world_values = [v / factor if factor else 0 for v in thai_values]
            source = "Fallback"
        data = {
            "labels": labels,
            "thai_values": [round(v, 2) for v in thai_values],
            "world_values": [round(v, 2) for v in world_values],
            "source": source,
            "updated_at": datetime.now().isoformat()
        }
        historical_cache.update({"data": data, "ts": now, "date": today})
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "ไม่สามารถโหลดข้อมูลย้อนหลังได้", "details": str(e)}), 500

# -------------------- Intraday API (Real-Time Chart) --------------------
intraday_cache = {}

@app.route("/api/intraday")
def api_intraday():
    try:
        now = time.time()
        time_range = request.args.get('range', '1d').lower()
        
        # Valid ranges and their corresponding sensible intervals for yfinance
        range_config = {
            '1d': '5m',
            '5d': '15m',
            '1w': '1h',
            '1mo': '1d'
        }
        
        if time_range not in range_config:
            time_range = '1d'
            
        interval = range_config[time_range]
        
        # Cache intraday data for 2 minutes per range to prevent spamming yfinance
        cache_key = f"intraday_{time_range}"
        if cache_key in intraday_cache and now - intraday_cache[cache_key]["ts"] < 120:
            return jsonify(intraday_cache[cache_key]["data"])
            
        labels = []
        thai_values = []
        world_values = []
        assoc_values = [] # Dynamic association prices
        source = ""
        
        if HAVE_YFINANCE:
            try:
                # Use GC=F (Gold Futures) as it is more reliable for long-term historical spot-like data than GLD ETF
                gld = yf.Ticker("GC=F")
                hist = gld.history(period=time_range, interval=interval)
                if not hist.empty:
                    usdthb = get_usdthb()
                    factor = usdthb * (15.244 / 31.1035) * 0.965
                    
                    for index, row in hist.iterrows():
                        # Format label based on interval and time range
                        if time_range == '1d':
                            label_str = index.strftime('%H:%M')
                        elif time_range in ['5d', '1w']:
                            label_str = index.strftime('%d %b %H:%M')
                        else:
                            label_str = index.strftime('%d %b') # Shows '15 Mar'
                            
                        labels.append(label_str)
                        usd_spot = to_float(row.get('Close')) if hasattr(row, "get") else to_float(row['Close'])
                        if usd_spot is None:
                            continue
                        thb_spot = float(usd_spot) * factor
                        world_values.append(round(float(usd_spot), 2))
                        thai_values.append(round(thb_spot, 2))
                        
                        # Generate a realistic historical association price (typically ~100-200 baht below spot or closely mirroring)
                        # We use rounding to nearest 50 to mimic the Thai Gold Association's pricing steps
                        assoc_historical = round(thb_spot / 50.0) * 50 - 50 
                        assoc_values.append(assoc_historical)
                        
                    source = f"Yahoo Finance ({time_range})"
                    
                    # Anchor to real Thai bar sell to prevent crazy scaling/jumps (esp. on free yfinance ranges)
                    try:
                        real_bar_sell = None
                        if thai_cache.get("data") and thai_cache["data"].get("bar_sell") is not None:
                            real_bar_sell = float(thai_cache["data"]["bar_sell"])
                        if real_bar_sell and thai_values:
                            basis = real_bar_sell - float(thai_values[-1])
                            thai_values = [round(float(v) + basis, 2) for v in thai_values]
                            assoc_values = [round((float(v) + basis) / 50.0) * 50 - 50 for v in assoc_values]
                            assoc_values[-1] = real_bar_sell
                    except Exception:
                        pass
            except Exception as e:
                print(f"Intraday fetch error for {time_range}: {e}")
        
        # Fallback if no yfinance or error
        if not labels:
            base_price = 41500.0
            if thai_cache["data"] and thai_cache["data"].get("bar_sell"):
                base_price = float(thai_cache["data"]["bar_sell"])
            
            usdthb = get_usdthb()
            factor = usdthb * (15.244 / 31.1035) * 0.965
            
            import math
            points_map = {
                '1d': 96,    # 5-min intervals
                '5d': 120,   # Hours
                '1w': 168,   # Hours
                '1mo': 30    # Days
            }
            points = points_map.get(time_range, 30)
            
            # Step size in minutes for the fallback date calculation
            step_map = {
                '1d': 5,
                '5d': 60,
                '1w': 60,
                '1mo': 1440
            }
            step_mins = step_map.get(time_range, 1440)
            
            for i in range(points):
                dt = datetime.now() - timedelta(minutes=(points-i)*step_mins)
                
                # Format
                if time_range == '1d':
                    lbl = dt.strftime('%H:%M')
                elif time_range in ['5d', '1w']:
                    lbl = dt.strftime('%d %b %H:%M')
                else:
                    lbl = dt.strftime('%d %b')
                
                labels.append(lbl)
                    
                noise = math.sin(i / 5.0) * 50 + math.cos(i / 2.0) * 20 + random.uniform(-10, 10)
                price_thb = base_price + noise
                thai_values.append(round(price_thb, 2))
                world_values.append(round(price_thb / factor, 2) if factor else 0)
                
                assoc_historical = round(price_thb / 50.0) * 50 - 50
                assoc_values.append(assoc_historical)
            
            thai_values[-1] = round(base_price, 2)
            world_values[-1] = round(base_price / factor, 2) if factor else 0
            # Force the last association value to be the real current price if we have it
            if thai_cache["data"] and thai_cache["data"].get("bar_sell"):
                assoc_values[-1] = float(thai_cache["data"]["bar_sell"])
                
            source = f"Synthetic Fallback ({time_range})"
            
        # Overwrite the very last association price with the live one from the cache to ensure the current end is 100% accurate
        if assoc_values and thai_cache["data"] and thai_cache["data"].get("bar_sell"):
             assoc_values[-1] = float(thai_cache["data"]["bar_sell"])

        data = {
            "labels": labels,
            "thai_values": thai_values,
            "world_values": world_values,
            "assoc_values": assoc_values,
            "source": source,
            "updated_at": datetime.now().isoformat()
        }
        
        intraday_cache[cache_key] = {"data": data, "ts": now}
        return jsonify(data)
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Failed to load intraday data", "details": str(e)}), 500

# -------------------- Forecast API (อัปเกรดแล้ว) --------------------
@app.route("/api/forecast", methods=["GET"])
def api_forecast():
    try:
        period = int(request.args.get("period", 7))
        model_name = str(request.args.get("model", "linear")).lower()
        hist_days = int(request.args.get("hist_days", 90)) # จำนวนวันอ้างอิง
        period = max(1, min(period, 90))
        hist_days = max(30, min(hist_days, 365))

        # --- 1. ดึงข้อมูลย้อนหลัง (Priority: price_cache DB → yfinance → synthetic) ---
        now = time.time()
        today = datetime.now().date().isoformat()
        source = ""

        # Try price_cache DB first (REAL Thai gold data)
        db_labels, db_values = build_series_from_db(days=365)
        if db_labels and db_values and len(db_values) >= 30:
            hist_labels, hist_values = db_labels, db_values
            source = "price_cache (Real Thai Data)"
        elif (historical_cache["data"] and historical_cache.get("date") == today):
            cache_data = historical_cache["data"]
            hist_labels = cache_data.get("labels")
            hist_values = cache_data.get("values") or cache_data.get("thai_values")
            source = "cached"
            if not hist_labels or not hist_values:
                hist_labels, hist_values = None, None
        else:
            try:
                hist_labels, hist_values, _ = build_series_with_world_from_yfinance(days=365)
                source = "Yahoo Finance (Adjusted)"
            except Exception as e:
                print(f"Historical fetch failed for forecast: {e}. Using synthetic fallback...")
                hist_labels, hist_values = build_historical_gold_data_free(days=365)
                source = "Synthetic (Estimated)"
            historical_cache.update({"data": {"labels": hist_labels, "values": hist_values}, "ts": now, "date": today})

        if not hist_labels or not hist_values:
            hist_labels, hist_values = build_historical_gold_data_free(days=365)
            source = source or "Synthetic (Estimated)"
        
        recent_values = hist_values[-hist_days:]
        if len(recent_values) < 10: raise ValueError("Not enough historical data.")

        # --- 2. Forecast with ARIMA (primary) or Linear Regression (fallback) ---
        forecasts = []
        upper_bound = []
        lower_bound = []
        confidence = 70.0
        last_actual = float(recent_values[-1])

        if HAVE_ARIMA and len(recent_values) >= 30:
            # === ARIMA Model ===
            try:
                model_name = 'ARIMA(5,1,0)'
                y = np.array(recent_values, dtype=float)
                arima_model = ARIMA(y, order=(5, 1, 0))
                arima_result = arima_model.fit()

                # Predict with confidence intervals
                forecast_result = arima_result.get_forecast(steps=period)
                forecasts = forecast_result.predicted_mean.tolist()
                
                # Anchoring: Adjust ARIMA to start from last_actual
                # (sometimes ARIMA mean starts a bit off)
                diff = last_actual - forecasts[0]
                # Decay the anchor over time (full anchor at t=0, half anchor at t=7)
                forecasts = [v + (diff * (0.8**i)) for i, v in enumerate(forecasts)]

                conf_int = forecast_result.conf_int(alpha=0.10)  # 90% CI
                lower_bound = (conf_int[:, 0] + diff).tolist()
                upper_bound = (conf_int[:, 1] + diff).tolist()

                # Confidence from AIC (lower AIC = better fit)
                aic = arima_result.aic
                confidence = max(50.0, min(95.0, 100.0 - abs(aic) / 100.0))

            except Exception as arima_err:
                print(f"ARIMA failed: {arima_err}, falling back to sklearn")
                ARIMA_FAILED = True
            else:
                ARIMA_FAILED = False

            if not ARIMA_FAILED:
                pass
            elif HAVE_SKLEARN:
                forecasts, upper_bound, lower_bound, confidence, model_name = _sklearn_forecast(recent_values, period)
            else:
                raise ValueError("No forecast model available")
        elif HAVE_SKLEARN:
            forecasts, upper_bound, lower_bound, confidence, model_name = _sklearn_forecast(recent_values, period)
        else:
            raise ValueError("No forecast model available (install statsmodels or scikit-learn)")

        # --- Sanity Clamp (ป้องกันการกระโดดผิดปกติในระยะสั้น) ---
        # ทองคำมักไม่เคลื่อนไหวเกิน 1.5% ต่อวันในสภาวะปกติ (ยกเว้นสงคราม/วิกฤต)
        max_daily_change = 0.015  # 1.5%
        clamped_forecasts = []
        prev_p = last_actual
        for i, p in enumerate(forecasts):
            # อนุญาตให้ความผันผวนสะสมตามจำนวนวัน (period)
            days_from_now = i + 1
            max_p = last_actual * (1 + max_daily_change * days_from_now)
            min_p = last_actual * (1 - max_daily_change * days_from_now)
            clamped_p = max(min_p, min(max_p, p))
            clamped_forecasts.append(clamped_p)
        
        forecasts = clamped_forecasts

        # Clamp to positive values
        forecasts = [max(0.0, round(v, 2)) for v in forecasts]
        upper_bound = [max(0.0, round(v, 2)) for v in upper_bound]
        lower_bound = [max(0.0, round(v, 2)) for v in lower_bound]

        # --- 3. Build Response (includes confidence bands) ---
        today_date = datetime.now().date()
        forecast_labels = [(today_date + timedelta(days=i)).isoformat() for i in range(1, period + 1)]

        trend = "ขาขึ้น" if forecasts[-1] >= recent_values[-1] else "ขาลง"
        summary = {
            "trend": trend,
            "max": max(forecasts),
            "min": min(forecasts),
            "confidence": round(confidence, 1),
            "source": source
        }
        response = {
            "labels": hist_labels[-30:] + forecast_labels,
            "history": hist_values[-30:],
            "forecast": forecasts,
            "upper_bound": upper_bound,
            "lower_bound": lower_bound,
            "summary": summary,
            "model": model_name,
            "period": period
        }

        return jsonify(response)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "ไม่สามารถสร้างการพยากรณ์ได้ในขณะนี้", "details": str(e)}), 500


def _sklearn_forecast(recent_values, period):
    """Fallback forecast using Linear Regression with anchoring and bootstrap confidence intervals."""
    model_name = 'Linear Regression'
    X_train = np.array(range(len(recent_values))).reshape(-1, 1)
    y_train = np.array(recent_values, dtype=float)

    model = LinearRegression()
    model.fit(X_train, y_train)

    X_future = np.array(range(len(recent_values), len(recent_values) + period)).reshape(-1, 1)
    preds = model.predict(X_future)

    # Anchoring: Shift prediction to start from last actual price
    last_actual = float(recent_values[-1])
    # Predicted value for the VERY SAME last data point
    last_fitted = model.predict(np.array([[len(recent_values) - 1]]))[0]
    offset = last_actual - last_fitted
    
    # Apply offset to predictions (decaying over time optional, but simple shift is usually fine for short term)
    preds = preds + offset

    r2 = model.score(X_train, y_train)
    confidence = max(50.0, min(95.0, r2 * 100))

    # Residual-based confidence interval (also shifted)
    residuals = y_train - model.predict(X_train)
    std_err = np.std(residuals)
    upper = (preds + 1.645 * std_err).tolist()  # 90% CI
    lower = (preds - 1.645 * std_err).tolist()

    return preds.tolist(), upper, lower, confidence, model_name

# -------------------- News API (Thai Gold News Scraper) --------------------
news_cache = {"data": None, "ts": 0}
NEWS_CACHE_DURATION = 600  # 10 minutes

@app.route("/api/news")
def api_news():
    now = time.time()

    # Return cached news if fresh
    if news_cache["data"] and (now - news_cache["ts"]) < NEWS_CACHE_DURATION:
        return jsonify(news_cache["data"])

    articles = []

    # --- Source 1: Google News RSS (real-time Thai gold news) ---
    try:
        from urllib.parse import quote
        query = quote("ราคาทองคำวันนี้")
        rss_url = f"https://news.google.com/rss/search?q={query}&hl=th&gl=TH&ceid=TH:th"
        r = requests.get(rss_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()

        soup = BeautifulSoup(r.content, "lxml-xml")
        items = soup.find_all("item", limit=10)

        for item in items:
            title = item.find("title")
            link = item.find("link")
            pub_date = item.find("pubDate")
            source_el = item.find("source")

            if title and link:
                # Parse pub date
                pub_str = ""
                if pub_date:
                    try:
                        from email.utils import parsedate_to_datetime
                        dt = parsedate_to_datetime(pub_date.text)
                        pub_str = dt.isoformat()
                    except Exception:
                        pub_str = pub_date.text

                articles.append({
                    "title": title.text.strip(),
                    "description": title.text.strip(),
                    "url": link.text.strip() if link.text else link.next_sibling.strip() if link.next_sibling else "#",
                    "urlToImage": None,
                    "publishedAt": pub_str,
                    "source": source_el.text.strip() if source_el else "Google News"
                })

        if articles:
            print(f"✅ Fetched {len(articles)} Thai gold news from Google News RSS")

    except Exception as e:
        print(f"⚠️ Google News RSS failed: {e}")

    # --- Source 2: NewsAPI fallback ---
    if len(articles) < 6:
        try:
            api_key = CONFIG.get("NEWSAPI_KEY")
            if api_key:
                url = "https://newsapi.org/v2/everything"
                params = {
                    "q": "ราคาทอง OR ทองคำ",
                    "sortBy": "publishedAt",
                    "apiKey": api_key,
                    "pageSize": 10,
                    "language": "th"
                }
                r = requests.get(url, params=params, timeout=10)
                if r.ok:
                    data = r.json()
                    for a in data.get("articles", []):
                        if a.get("title") and a.get("url"):
                            articles.append({
                                "title": a["title"],
                                "description": a.get("description"),
                                "url": a["url"],
                                "urlToImage": a.get("urlToImage"),
                                "publishedAt": a.get("publishedAt"),
                                "source": a.get("source", {}).get("name")
                            })
        except Exception as e:
            print(f"⚠️ NewsAPI fallback failed: {e}")

    # --- Source 3: Static fallback (last resort) ---
    if not articles:
        articles = [
            {
                "title": "สมาคมค้าทองคำประกาศราคาทองวันนี้ ปรับตัวสูงขึ้นรับความไม่แน่นอนทางเศรษฐกิจ",
                "description": "ราคาทองคำในประเทศปรับตัวสูงขึ้น ตามทิศทางราคาทองคำตลาดโลก",
                "url": "https://www.goldtraders.or.th/",
                "urlToImage": "https://images.unsplash.com/photo-1610375461246-83df859d849d?w=800",
                "publishedAt": datetime.now().isoformat(),
                "source": "สมาคมค้าทองคำ"
            },
            {
                "title": "เจาะลึกทิศทางราคาทองคำ: แนวโน้มระยะสั้นและระยะกลาง",
                "description": "นักวิเคราะห์ประเมินทิศทางราคาทองคำโลกและทองคำไทย",
                "url": "https://www.goldtraders.or.th/",
                "urlToImage": "https://images.unsplash.com/photo-1589758438368-0ad531db3366?w=800",
                "publishedAt": (datetime.now() - timedelta(hours=4)).isoformat(),
                "source": "ประชาชาติธุรกิจ"
            }
        ]

    # Cache the result
    news_cache["data"] = articles[:10]
    news_cache["ts"] = now

    return jsonify(articles[:10])

# -------------------- Health & Run --------------------
# @app.route("/api/health")
def old_api_health():
    return jsonify({"ok": True, "time": datetime.now().isoformat()})

def send_alert_email_smtp(alert, current_price):
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "").strip()
    from_email = os.getenv("SMTP_FROM_EMAIL", smtp_user).strip() or smtp_user
    from_name = os.getenv("SMTP_FROM_NAME", "Gold Price Today").strip()

    if not smtp_host or not smtp_user or not smtp_pass or not from_email:
        print("SMTP config incomplete. Skip real email sending.")
        return False

    to_email = (alert.get("receiver_email") or alert.get("notify_email") or alert.get("email") or "").strip()
    if not to_email:
        print("No recipient email in alert row.")
        return False

    ptype = alert.get("gold_type", "bar")
    atype = alert.get("alert_type", "above")
    target_price = float(alert.get("target_price") or 0)
    user_name = alert.get("name") or "ลูกค้า"
    type_map = {"bar": "ทองคำแท่ง", "ornament": "ทองรูปพรรณ", "world": "ทองโลก (USD/oz)"}
    type_text = type_map.get(ptype, ptype)
    condition_text = "สูงกว่า หรือ เท่ากับ" if atype == "above" else "ต่ำกว่า หรือ เท่ากับ"
    is_world = ptype == "world"
    money_prefix = "$" if is_world else "฿"
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

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.ehlo()
            if smtp_port == 587:
                server.starttls()
                server.ehlo()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, [to_email], msg.as_string())
        return True
    except Exception as e:
        print(f"SMTP send failed to {to_email}: {e}")
        return False

def send_forecast_email_smtp(payload):
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "").strip()
    from_email = os.getenv("SMTP_FROM_EMAIL", smtp_user).strip() or smtp_user
    from_name = os.getenv("SMTP_FROM_NAME", "Gold Price Today").strip()

    if not smtp_host or not smtp_user or not smtp_pass or not from_email:
        print("SMTP config incomplete. Skip forecast email sending.")
        return False

    to_email = (payload.get("email") or "").strip()
    if not to_email:
        return False

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
            <p style="margin-top:16px;">ระบบได้บันทึกประวัติไว้ให้แล้ว คุณไม่จำเป็นต้องเข้าเว็บมาดูทุกครั้ง</p>
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

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.ehlo()
            if smtp_port == 587:
                server.starttls()
                server.ehlo()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, [to_email], msg.as_string())
        return True
    except Exception as e:
        print(f"Forecast SMTP send failed to {to_email}: {e}")
        return False

def send_forecast_result_email_smtp(payload):
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "").strip()
    from_email = os.getenv("SMTP_FROM_EMAIL", smtp_user).strip() or smtp_user
    from_name = os.getenv("SMTP_FROM_NAME", "Gold Price Today").strip()

    if not smtp_host or not smtp_user or not smtp_pass or not from_email:
        print("SMTP config incomplete. Skip forecast result email sending.")
        return False

    to_email = (payload.get("email") or "").strip()
    if not to_email:
        return False

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

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.ehlo()
            if smtp_port == 587:
                server.starttls()
                server.ehlo()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, [to_email], msg.as_string())
        return True
    except Exception as e:
        print(f"Forecast result SMTP send failed to {to_email}: {e}")
        return False

@app.route('/api/forecast/send-email', methods=['POST', 'OPTIONS'])
def send_forecast_email():
    if request.method == 'OPTIONS':
        return jsonify(success=True)
    try:
        payload = request.json or {}
        if not payload.get("email") or not payload.get("target_date"):
            return jsonify(success=False, message="Missing required fields"), 400
        sent = send_forecast_email_smtp(payload)
        if sent:
            return jsonify(success=True, message="Forecast email sent")
        return jsonify(success=False, message="Forecast email send failed"), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, message=str(e)), 500


def _job_token_ok(req) -> bool:
    expected = (os.getenv("JOB_TOKEN") or "").strip()
    if not expected:
        return False
    auth = (req.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        got = auth.split(" ", 1)[1].strip()
        return hmac.compare_digest(got, expected)
    got = (req.headers.get("X-Job-Token") or "").strip()
    if got:
        return hmac.compare_digest(got, expected)
    return False


def _line_push(line_user_id: str, text: str) -> bool:
    token = (os.getenv("LINE_CHANNEL_ACCESS_TOKEN") or "").strip()
    if not token or not line_user_id:
        return False
    try:
        r = requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            json={
                "to": line_user_id,
                "messages": [{"type": "text", "text": text}],
            },
            timeout=10,
        )
        if not r.ok:
            print(f"LINE push failed: {r.status_code} {r.text[:200]}")
        return bool(r.ok)
    except Exception:
        traceback.print_exc()
        return False


def run_scheduled_jobs_once():
    stats = {
        "ok": True,
        "errors": [],
        "checked_alerts": 0,
        "triggered_alerts": 0,
        "verified_forecasts": 0,
        "line_sent": 0,
        "email_sent": 0,
    }

    try:
        thai_data = refresh_thai_cache()
    except Exception as e:
        stats["ok"] = False
        stats["errors"].append(f"thai_refresh_failed: {e}")
        thai_data = thai_cache.get("data") or {}
    try:
        world_data = refresh_world_cache()
    except Exception as e:
        stats["ok"] = False
        stats["errors"].append(f"world_refresh_failed: {e}")
        world_data = world_cache.get("data") or {}

    try:
        save_daily_price()
    except Exception as e:
        stats["ok"] = False
        stats["errors"].append(f"save_daily_price_failed: {e}")

    current_prices = {
        "bar": to_float(thai_data.get("bar_sell")) if thai_data else 0,
        "bar_buy": to_float(thai_data.get("bar_buy")) if thai_data else 0,
        "ornament": to_float(thai_data.get("ornament_sell")) if thai_data else 0,
        "world": to_float(world_data.get("price_usd_per_ounce")) if world_data else 0,
    }

    try:
        conn = get_db_connection()
    except Exception as e:
        stats["ok"] = False
        stats["errors"].append(f"db_connect_failed: {e}")
        stats["hint"] = "ตรวจสอบ DB_HOST/DB_USER/DB_PASS/DB_NAME ว่าเป็นฐานข้อมูลที่เข้าถึงได้จาก Render (ห้ามเป็น localhost)"
        return stats
    try:
        with conn.cursor() as cursor:
            # ---- Price Alerts ----
            alerts = []
            try:
                try:
                    cursor.execute(
                        """
                        SELECT pa.*, u.name, u.email, u.line_user_id,
                               COALESCE(pa.notify_email, u.email) AS receiver_email
                        FROM price_alerts pa
                        INNER JOIN users u ON u.id = pa.user_id
                        WHERE pa.triggered = 0
                        """
                    )
                except Exception:
                    # รองรับกรณี DB ยังไม่มีคอลัมน์ line_user_id
                    cursor.execute(
                        """
                        SELECT pa.*, u.name, u.email,
                               COALESCE(pa.notify_email, u.email) AS receiver_email
                        FROM price_alerts pa
                        INNER JOIN users u ON u.id = pa.user_id
                        WHERE pa.triggered = 0
                        """
                    )
                alerts = cursor.fetchall() or []
            except Exception as e:
                stats["ok"] = False
                stats["errors"].append(f"alerts_query_failed: {e}")

            stats["checked_alerts"] = len(alerts)

            for alert in alerts:
                try:
                    target = float(alert.get("target_price") or 0)
                    ptype = alert.get("gold_type")
                    atype = alert.get("alert_type")
                    curr = current_prices.get(ptype, 0)
                    if not curr or not target:
                        continue

                    trigger = (atype == "above" and curr >= target) or (atype == "below" and curr <= target)
                    if not trigger:
                        continue

                    line_user_id = alert.get("line_user_id")
                    user_name = alert.get("name") or "ผู้ใช้"
                    type_map = {"bar": "ทองคำแท่ง", "ornament": "ทองรูปพรรณ", "world": "ทองโลก (USD/oz)"}
                    type_text = type_map.get(ptype, str(ptype))
                    cond_text = "สูงกว่า/เท่ากับ" if atype == "above" else "ต่ำกว่า/เท่ากับ"
                    money_prefix = "$" if ptype == "world" else "฿"
                    msg = (
                        f"🔔 แจ้งเตือนราคาทอง\n"
                        f"- ผู้ใช้: {user_name}\n"
                        f"- ประเภท: {type_text}\n"
                        f"- เงื่อนไข: {cond_text} {money_prefix}{target:,.2f}\n"
                        f"- ราคาปัจจุบัน: {money_prefix}{curr:,.2f}"
                    )

                    line_sent = False
                    if line_user_id:
                        line_sent = _line_push(line_user_id, msg)
                        if line_sent:
                            stats["line_sent"] += 1

                    email_sent = False
                    if not line_sent:
                        email_sent = send_alert_email_smtp(alert, curr)
                        if email_sent:
                            stats["email_sent"] += 1

                    if line_sent or email_sent:
                        cursor.execute(
                            "UPDATE price_alerts SET triggered=1, triggered_at=NOW() WHERE id=%s",
                            (alert["id"],),
                        )
                        stats["triggered_alerts"] += 1
                except Exception:
                    traceback.print_exc()

            # ---- Forecast Verification ----
            due_forecasts = []
            try:
                try:
                    cursor.execute(
                        """
                        SELECT sf.id, sf.user_id, sf.target_date, sf.max_price, sf.min_price,
                               u.name, u.email, u.line_user_id
                        FROM saved_forecasts sf
                        INNER JOIN users u ON u.id = sf.user_id
                        WHERE sf.verified_at IS NULL
                          AND sf.target_date <= CURDATE()
                        ORDER BY sf.target_date ASC
                        LIMIT 100
                        """
                    )
                except Exception:
                    cursor.execute(
                        """
                        SELECT sf.id, sf.user_id, sf.target_date, sf.max_price, sf.min_price,
                               u.name, u.email
                        FROM saved_forecasts sf
                        INNER JOIN users u ON u.id = sf.user_id
                        WHERE sf.verified_at IS NULL
                          AND sf.target_date <= CURDATE()
                        ORDER BY sf.target_date ASC
                        LIMIT 100
                        """
                    )
                due_forecasts = cursor.fetchall() or []
            except Exception as e:
                stats["ok"] = False
                stats["errors"].append(f"forecasts_query_failed: {e}")
            for row in due_forecasts:
                try:
                    target_date = row.get("target_date")
                    pred_max = float(row.get("max_price") or 0)
                    pred_min = float(row.get("min_price") or 0)
                    if pred_min > pred_max:
                        pred_min, pred_max = pred_max, pred_min

                    cursor.execute(
                        """
                        SELECT bar_sell, bar_buy
                        FROM price_cache
                        WHERE date = %s
                        ORDER BY created_at DESC
                        LIMIT 1
                        """,
                        (target_date,),
                    )
                    cache_row = cursor.fetchone() or {}
                    actual_sell = to_float(cache_row.get("bar_sell"))
                    actual_buy = to_float(cache_row.get("bar_buy"))

                    if (actual_sell is None or actual_buy is None) and str(target_date) == datetime.now().date().isoformat():
                        actual_sell = actual_sell if actual_sell is not None else to_float(current_prices.get("bar"))
                        actual_buy = actual_buy if actual_buy is not None else to_float(current_prices.get("bar_buy"))

                    if actual_sell is None or actual_buy is None:
                        continue

                    is_accurate = (pred_min <= actual_sell <= pred_max) and (pred_min <= actual_buy <= pred_max)

                    cursor.execute(
                        """
                        UPDATE saved_forecasts
                        SET actual_max_price=%s,
                            actual_min_price=%s,
                            verified_at=NOW()
                        WHERE id=%s
                        """,
                        (actual_sell, actual_buy, row["id"]),
                    )
                    stats["verified_forecasts"] += 1

                    target_date_display = str(target_date)
                    try:
                        d = datetime.fromisoformat(str(target_date)[:10])
                        target_date_display = f"{d.day}/{d.month}/{d.year + 543}"
                    except Exception:
                        pass

                    status_text = "แม่นยำ ✅" if is_accurate else "ไม่แม่นยำ ❌"
                    msg = (
                        f"📊 ผลพยากรณ์ทองคำ ({target_date_display})\n"
                        f"- ผล: {status_text}\n"
                        f"- ช่วงพยากรณ์: ฿{pred_min:,.2f} - ฿{pred_max:,.2f}\n"
                        f"- ราคาจริง (ขายออก): ฿{actual_sell:,.2f}\n"
                        f"- ราคาจริง (รับซื้อ): ฿{actual_buy:,.2f}"
                    )

                    line_sent = False
                    line_user_id = row.get("line_user_id")
                    if line_user_id:
                        line_sent = _line_push(line_user_id, msg)
                        if line_sent:
                            stats["line_sent"] += 1

                    if not line_sent:
                        sent = send_forecast_result_email_smtp(
                            {
                                "email": row.get("email"),
                                "name": row.get("name"),
                                "target_date_display": target_date_display,
                                "pred_min": pred_min,
                                "pred_max": pred_max,
                                "actual_buy": actual_buy,
                                "actual_sell": actual_sell,
                                "is_accurate": is_accurate,
                            }
                        )
                        if sent:
                            stats["email_sent"] += 1
                except Exception:
                    traceback.print_exc()

        conn.commit()
    finally:
        conn.close()

    return stats


@app.route("/api/jobs/run", methods=["POST"])
def api_run_jobs():
    if not _job_token_ok(request):
        return jsonify(ok=False, message="Unauthorized"), 401
    try:
        result = run_scheduled_jobs_once()
        return jsonify(result), 200
    except Exception as e:
        traceback.print_exc()
        # ให้ Worker/cron อ่าน error ได้ แต่ไม่ทำให้เรียก API แล้วล้มด้วย 500
        return jsonify(ok=False, message=str(e)), 200


def background_alert_checker():
    """ตรวจสอบ alerts และส่งอีเมลจริงผ่าน SMTP"""
    while True:
        try:
            time.sleep(60) # Note: For testing, changing this to 60s. Can be reverted to 300s (5min) later.
            
            try:
                thai_data = refresh_thai_cache()
            except Exception:
                thai_data = thai_cache.get("data")
            try:
                world_data = refresh_world_cache()
            except Exception:
                world_data = world_cache.get("data")

            try:
                save_daily_price()
            except Exception:
                pass
            
            current_prices = {
                'bar': to_float(thai_data.get('bar_sell')) if thai_data else 0,
                'bar_buy': to_float(thai_data.get('bar_buy')) if thai_data else 0,
                'ornament': to_float(thai_data.get('ornament_sell')) if thai_data else 0,
                'world': to_float(world_data.get('price_usd_per_ounce')) if world_data else 0
            }

            conn = get_db_connection()
            try:
                with conn.cursor() as cursor:
                    if current_prices['bar'] or current_prices['world']:
                        cursor.execute("""
                            SELECT pa.*, u.name, COALESCE(pa.notify_email, u.email) AS receiver_email
                            FROM price_alerts pa
                            INNER JOIN users u ON u.id = pa.user_id
                            WHERE pa.triggered = 0
                        """)
                        alerts = cursor.fetchall()
                        
                        for alert in alerts:
                            trigger = False
                            target = float(alert['target_price'])
                            ptype = alert['gold_type']
                            atype = alert['alert_type']
                            
                            curr = current_prices.get(ptype, 0)
                            
                            if curr is not None and curr > 0:
                                if atype == 'above' and curr >= target:
                                    trigger = True
                                elif atype == 'below' and curr <= target:
                                    trigger = True

                            if trigger:
                                email_sent = send_alert_email_smtp(alert, curr)
                                if email_sent:
                                    cursor.execute("UPDATE price_alerts SET triggered=1, triggered_at=NOW() WHERE id=%s", (alert['id'],))
                                    print(f"🔔 Sent alert email to {alert.get('receiver_email')} (alert #{alert['id']})")
                                else:
                                    print(f"❌ Failed sending alert #{alert['id']} to {alert.get('receiver_email')}")

                    cursor.execute("""
                        SELECT sf.id, sf.user_id, sf.target_date, sf.max_price, sf.min_price, sf.created_at, u.name, u.email
                        FROM saved_forecasts sf
                        INNER JOIN users u ON u.id = sf.user_id
                        WHERE sf.verified_at IS NULL
                          AND sf.target_date <= CURDATE()
                        ORDER BY sf.target_date ASC
                        LIMIT 100
                    """)
                    due_forecasts = cursor.fetchall()

                    for row in due_forecasts:
                        target_date = row.get('target_date')
                        pred_max = float(row.get('max_price') or 0)
                        pred_min = float(row.get('min_price') or 0)
                        if pred_min > pred_max:
                            pred_min, pred_max = pred_max, pred_min

                        actual_sell = None
                        actual_buy = None

                        cursor.execute("""
                            SELECT bar_sell, bar_buy
                            FROM price_cache
                            WHERE date = %s
                            ORDER BY created_at DESC
                            LIMIT 1
                        """, (target_date,))
                        cache_row = cursor.fetchone()
                        if cache_row:
                            actual_sell = to_float(cache_row.get('bar_sell'))
                            actual_buy = to_float(cache_row.get('bar_buy'))

                        if (actual_sell is None or actual_buy is None) and str(target_date) == datetime.now().date().isoformat():
                            actual_sell = actual_sell if actual_sell is not None else to_float(current_prices.get('bar'))
                            actual_buy = actual_buy if actual_buy is not None else to_float(current_prices.get('bar_buy'))

                        if actual_sell is None or actual_buy is None:
                            continue

                        is_accurate = (pred_min <= actual_sell <= pred_max) and (pred_min <= actual_buy <= pred_max)
                        cursor.execute("""
                            UPDATE saved_forecasts
                            SET actual_max_price=%s,
                                actual_min_price=%s,
                                verified_at=NOW()
                            WHERE id=%s
                        """, (actual_sell, actual_buy, row['id']))

                        target_date_display = str(target_date)
                        try:
                            d = datetime.fromisoformat(str(target_date)[:10])
                            target_date_display = f"{d.day}/{d.month}/{d.year + 543}"
                        except Exception:
                            pass

                        send_forecast_result_email_smtp({
                            "email": row.get("email"),
                            "name": row.get("name"),
                            "target_date_display": target_date_display,
                            "pred_min": pred_min,
                            "pred_max": pred_max,
                            "actual_buy": actual_buy,
                            "actual_sell": actual_sell,
                            "is_accurate": is_accurate
                        })
                
                conn.commit()
            finally:
                conn.close()
                
        except Exception as e:
            print(f"Error executing background cron: {e}")

# Start the background checker
if (os.getenv("ENABLE_BACKGROUND_CHECKER") or "true").strip().lower() in ("1", "true", "yes", "on"):
    threading.Thread(target=background_alert_checker, daemon=True).start()
else:
    print("Background checker disabled (ENABLE_BACKGROUND_CHECKER=false)")


# -------------------- Alert System (Fixed) --------------------
@app.route('/api/alerts/create', methods=['POST', 'OPTIONS'])
def create_alert():
    if request.method == 'OPTIONS':
        return jsonify(success=True)

    try:
        data = request.json
        if not data:
            return jsonify(success=False, message="No data provided"), 400

        target_price = float(data.get('target_price', 0))
        gold_type = data.get('gold_type', 'bar')
        alert_type = data.get('alert_type', 'above')
        email = data.get('email', '')

        if target_price <= 0 or not email:
            return jsonify(success=False, message="Invalid parameters"), 400

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Resolve user_id from email (no hardcode)
                cursor.execute("SELECT id FROM users WHERE email=%s", (email,))
                user_row = cursor.fetchone()

                if not user_row:
                    return jsonify(success=False, message="User not found. Please register first."), 404

                user_id = user_row['id']

                sql = """
                    INSERT INTO price_alerts (user_id, target_price, gold_type, alert_type, channel_email, notify_email)
                    VALUES (%s, %s, %s, %s, 1, %s)
                """
                cursor.execute(sql, (user_id, target_price, gold_type, alert_type, email))
            conn.commit()
            return jsonify(success=True, message="Alert saved successfully")
        finally:
            conn.close()

    except Exception as e:
        if isinstance(e, pymysql.err.IntegrityError):
            return jsonify(success=False, message="มีการตั้งค่าแจ้งเตือนนี้แล้ว"), 409
        traceback.print_exc()
        return jsonify(success=False, message=str(e)), 500

@app.route('/api/alerts', methods=['GET', 'OPTIONS'])
def list_alerts():
    if request.method == 'OPTIONS':
        return jsonify(success=True)

    try:
        email = request.args.get('email', '')
        if not email:
            return jsonify(success=False, message="Email required"), 400

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, user_id, target_price, alert_type, gold_type, channel_email, notify_email, triggered, triggered_at, created_at
                    FROM price_alerts
                    WHERE notify_email=%s
                    ORDER BY created_at DESC
                """, (email,))
                alerts = cursor.fetchall()
            # Return as 'items' to match frontend expectations
            return jsonify(success=True, items=alerts)
        finally:
            conn.close()

    except Exception as e:
        traceback.print_exc()
        return jsonify(success=False, message=str(e)), 500

@app.route('/api/alerts/<int:alert_id>', methods=['DELETE', 'OPTIONS'])
def delete_alert(alert_id):
    if request.method == 'OPTIONS':
        return jsonify(success=True)

    try:
        email = request.args.get('email', '')
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


def _line_signature_ok(body: bytes, signature: str) -> bool:
    secret = os.getenv("LINE_CHANNEL_SECRET", "")
    if not secret or not signature:
        return True
    mac = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def _line_reply(reply_token: str, text: str) -> None:
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not token or not reply_token:
        return
    try:
        r = requests.post(
            "https://api.line.me/v2/bot/message/reply",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            json={
                "replyToken": reply_token,
                "messages": [{"type": "text", "text": text}],
            },
            timeout=10,
        )
        if not r.ok:
            print(f"LINE reply failed: {r.status_code} {r.text[:200]}")
    except Exception:
        traceback.print_exc()


def _line_get_display_name(line_user_id: str):
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not token or not line_user_id:
        return None
    try:
        r = requests.get(
            f"https://api.line.me/v2/bot/profile/{line_user_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if r.ok:
            return (r.json() or {}).get("displayName")
    except Exception:
        traceback.print_exc()
    return None


def _line_menu_text() -> str:
    return (
        "เมนูคำสั่ง (พิมพ์ได้เลย)\n"
        "- ราคา : ดูราคาล่าสุด (จากระบบ cache)\n"
        "- สถานะ : ดูว่าเชื่อมบัญชีแล้วหรือยัง\n"
        "- LINK-123456 : เชื่อมบัญชี (ใช้รหัสจากหน้าเว็บ)\n"
        "- ยกเลิก : ยกเลิกการเชื่อมต่อ LINE\n"
        "- ช่วยเหลือ : ดูเมนูนี้อีกครั้ง"
    )


def _line_get_cached_prices_text():
    try:
        thai = thai_cache.get("data") or {}
        world = world_cache.get("data") or {}
        have_thai = all(thai.get(k) is not None for k in ("bar_buy", "bar_sell", "ornament_buy", "ornament_sell"))
        have_world = world.get("price_usd_per_ounce") is not None
        if not have_thai and not have_world:
            return None

        parts = []
        if have_thai:
            parts.append("ราคาทองไทย (ล่าสุด)")
            parts.append(f"- ทองคำแท่ง รับซื้อ: ฿{float(thai['bar_buy']):,.2f} | ขายออก: ฿{float(thai['bar_sell']):,.2f}")
            parts.append(
                f"- ทองรูปพรรณ รับซื้อ: ฿{float(thai['ornament_buy']):,.2f} | ขายออก: ฿{float(thai['ornament_sell']):,.2f}"
            )
        if have_world:
            parts.append(f"ทองโลก (XAUUSD): ${float(world['price_usd_per_ounce']):,.2f}/oz")
        if thai.get("date") or thai.get("update_round"):
            parts.append(f"อัปเดต: {thai.get('date','')} {thai.get('update_round','')}".strip())
        return "\n".join(parts)
    except Exception:
        traceback.print_exc()
        return None


def _line_unlink(conn, line_user_id: str) -> bool:
    if not line_user_id:
        return False
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE users SET line_user_id=NULL, line_display_name=NULL WHERE line_user_id=%s",
            (line_user_id,),
        )
        return cursor.rowcount > 0


def _line_status_text(conn, line_user_id: str) -> str:
    if not line_user_id:
        return "ไม่พบ LINE userId"
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT id, name FROM users WHERE line_user_id=%s AND is_active=1 LIMIT 1",
            (line_user_id,),
        )
        user = cursor.fetchone()
    if user:
        name = user.get("name") or "ผู้ใช้"
        return f"✅ เชื่อมต่อแล้วกับบัญชี: {name}"
    return "ยังไม่ได้เชื่อมต่อบัญชีครับ\nพิมพ์ LINK-123456 (รับรหัสจากหน้าเว็บ) เพื่อเชื่อมบัญชี"


@app.route("/webhook", methods=["POST", "GET"])
def line_webhook():
    if request.method == "GET":
        return "OK", 200

    body = request.get_data() or b""
    signature = request.headers.get("X-Line-Signature", "")
    if not _line_signature_ok(body, signature):
        return "Invalid signature", 400

    payload = request.get_json(silent=True) or {}
    events = payload.get("events") or []

    for event in events:
        try:
            if (event or {}).get("type") != "message":
                continue
            msg = (event.get("message") or {})
            if msg.get("type") != "text":
                continue

            reply_token = event.get("replyToken")
            text = (msg.get("text") or "").strip()
            source = event.get("source") or {}
            line_user_id = source.get("userId")

            if not reply_token:
                continue

            print(f"LINE inbound: {text}")

            t = text.lower()
            if t in ("help", "menu", "ช่วยเหลือ", "เมนู", "?"):
                _line_reply(reply_token, _line_menu_text())
                continue

            if t in ("price", "ราคา", "ราคาทอง", "ทอง", "gold"):
                price_text = _line_get_cached_prices_text()
                _line_reply(
                    reply_token,
                    price_text
                    or "ตอนนี้ยังไม่มีข้อมูลราคาในระบบ cache\nลองเปิดหน้าเว็บสักครู่ แล้วพิมพ์ \"ราคา\" อีกครั้งครับ",
                )
                continue

            if t in ("status", "สถานะ", "unlink", "ยกเลิก", "เลิก", "disconnect") or re.match(
                r"^LINK-(\d{6})$", text, flags=re.IGNORECASE
            ):
                try:
                    conn = get_db_connection()
                except Exception:
                    traceback.print_exc()
                    _line_reply(reply_token, "ระบบฐานข้อมูลมีปัญหาชั่วคราว ลองใหม่อีกครั้งครับ")
                    continue

                try:
                    if t in ("status", "สถานะ"):
                        _line_reply(reply_token, _line_status_text(conn, line_user_id))
                        continue

                    if t in ("unlink", "ยกเลิก", "เลิก", "disconnect"):
                        ok = _line_unlink(conn, line_user_id)
                        conn.commit()
                        _line_reply(
                            reply_token,
                            "✅ ยกเลิกการเชื่อมต่อเรียบร้อยแล้ว" if ok else "ไม่พบการเชื่อมต่อที่ต้องยกเลิก",
                        )
                        continue

                    m = re.match(r"^LINK-(\d{6})$", text, flags=re.IGNORECASE)
                    if not m:
                        _line_reply(reply_token, "พิมพ์ \"ช่วยเหลือ\" เพื่อดูเมนูคำสั่ง")
                        continue

                    code = m.group(1)
                    display_name = _line_get_display_name(line_user_id) if line_user_id else None

                    with conn.cursor() as cursor:
                        cursor.execute(
                            "SELECT id, name FROM users WHERE verification_token=%s AND is_active=1 LIMIT 1",
                            (code,),
                        )
                        user = cursor.fetchone()

                        if not user:
                            _line_reply(reply_token, "❌ รหัสเชื่อมต่อไม่ถูกต้อง หรือหมดอายุแล้วครับ")
                            continue

                        cursor.execute(
                            "UPDATE users SET line_user_id=%s, line_display_name=%s, verification_token=NULL WHERE id=%s",
                            (line_user_id, display_name, user["id"]),
                        )
                    conn.commit()

                    name = user.get("name") or "ผู้ใช้"
                    _line_reply(
                        reply_token,
                        f"✅ เชื่อมต่อสำเร็จ! สวัสดีคุณ {name}\nต่อไปนี้คุณจะได้รับแจ้งเตือนราคาทองผ่าน LINE นี้ครับ",
                    )
                    continue
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass

            _line_reply(
                reply_token,
                "พิมพ์ \"ช่วยเหลือ\" เพื่อดูเมนูคำสั่ง\nหรือส่งรหัสเชื่อมต่อจากหน้าเว็บไซต์ในรูปแบบ LINK-123456 เพื่อเชื่อมบัญชีครับ",
            )
        except Exception:
            traceback.print_exc()

    return "OK", 200


if __name__ == '__main__':
    port = int(os.getenv("PORT", "5000"))
    debug = (os.getenv("APP_DEBUG", "true").strip().lower() in ("1", "true", "yes", "on"))
    app.run(host="0.0.0.0", port=port, debug=debug)
# ===================== End of server.py =====================
