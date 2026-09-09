"""database/connection.py — DB connection pooling and schema-fix utilities."""
import os
import sys
import threading
import pymysql

try:
    import dbutils
    import dbutils.pooled_db
    sys.modules.setdefault("DBUtils", dbutils)
    sys.modules.setdefault("DBUtils.pooled_db", dbutils.pooled_db)
    from dbutils.pooled_db import PooledDB
except ImportError:
    try:
        from DBUtils.PooledDB import PooledDB
    except ImportError:
        PooledDB = None

_pool = None
_pool_config = None
_pool_lock = threading.Lock()


USER_TABLE_ALTERS = {
    "name": "ALTER TABLE users ADD COLUMN name VARCHAR(100) NULL",
    "verification_token": "ALTER TABLE users ADD COLUMN verification_token VARCHAR(100) NULL",
    "line_user_id": "ALTER TABLE users ADD COLUMN line_user_id VARCHAR(100) NULL",
    "line_display_name": "ALTER TABLE users ADD COLUMN line_display_name VARCHAR(100) NULL",
    "push_subscription": "ALTER TABLE users ADD COLUMN push_subscription LONGTEXT NULL",
}


def _get_connection_config():
    host = os.getenv("DB_HOST")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    database = os.getenv("DB_NAME")
    port = int(os.getenv("DB_PORT", 3306))

    connect_options = {}
    ssl_ca = (os.getenv("DB_SSL_CA") or "").strip()
    if ssl_ca:
        connect_options["ssl"] = {"ca": ssl_ca, "check_hostname": True}

    mincached = int(os.getenv("DB_POOL_MIN_CACHED", 0))
    maxcached = int(os.getenv("DB_POOL_MAX_CACHED", 10))
    maxconnections = int(os.getenv("DB_POOL_MAX_CONNECTIONS", 20))
    blocking = os.getenv("DB_POOL_BLOCKING", "true").lower() in ("1", "true", "yes")

    return {
        "host": host,
        "user": user,
        "password": password,
        "database": database,
        "port": port,
        "ssl_ca": ssl_ca,
        "connect_options": connect_options,
        "mincached": mincached,
        "maxcached": maxcached,
        "maxconnections": maxconnections,
        "blocking": blocking,
    }


def init_db_pool(reset=False, expected_key=None, **kwargs):
    """Initialize or reset the global PooledDB pool in a thread-safe manner."""
    global _pool, _pool_config
    with _pool_lock:
        if _pool is not None and not reset and (expected_key is None or _pool_config == expected_key):
            return _pool

        if _pool is not None:
            try:
                _pool.close()
            except Exception:
                pass
            _pool = None
            _pool_config = None

        cfg = _get_connection_config()
        cfg.update(kwargs)

        if PooledDB is None:
            return None

        # Build PooledDB wrapping PyMySQL with DictCursor
        _pool = PooledDB(
            creator=pymysql,
            mincached=cfg.get("mincached", 0),
            maxcached=cfg.get("maxcached", 10),
            maxconnections=cfg.get("maxconnections", 20),
            blocking=cfg.get("blocking", True),
            ping=1,
            host=cfg.get("host"),
            user=cfg.get("user"),
            password=cfg.get("password"),
            database=cfg.get("database"),
            port=cfg.get("port"),
            cursorclass=pymysql.cursors.DictCursor,
            **cfg.get("connect_options", {}),
        )
        _pool_config = (
            cfg.get("host"),
            cfg.get("user"),
            cfg.get("password"),
            cfg.get("database"),
            cfg.get("port"),
            cfg.get("ssl_ca"),
            cfg.get("mincached"),
            cfg.get("maxcached"),
            cfg.get("maxconnections"),
            cfg.get("blocking"),
            getattr(pymysql, "connect", None),
        )
        return _pool


def get_db_pool():
    """Get the active PooledDB pool, initializing if necessary."""
    global _pool, _pool_config
    cfg = _get_connection_config()
    current_key = (
        cfg["host"],
        cfg["user"],
        cfg["password"],
        cfg["database"],
        cfg["port"],
        cfg["ssl_ca"],
        cfg["mincached"],
        cfg["maxcached"],
        cfg["maxconnections"],
        cfg["blocking"],
        getattr(pymysql, "connect", None),
    )
    if _pool is None or _pool_config != current_key:
        return init_db_pool(reset=False, expected_key=current_key)
    return _pool


def close_db_pool():
    """Explicitly close all idle connections and reset the pool."""
    global _pool, _pool_config
    with _pool_lock:
        if _pool is not None:
            try:
                _pool.close()
            except Exception:
                pass
            _pool = None
            _pool_config = None


def get_db_connection():
    """Get a database connection from the PooledDB pool.

    Falls back to direct pymysql.connect if PooledDB is unavailable.
    """
    pool = get_db_pool()
    if pool is not None:
        return pool.connection()

    # Fallback if PooledDB is unavailable
    cfg = _get_connection_config()
    return pymysql.connect(
        host=cfg["host"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        port=cfg["port"],
        cursorclass=pymysql.cursors.DictCursor,
        **cfg["connect_options"],
    )


def _looks_like_missing_column(exc: Exception) -> bool:
    msg = str(exc or "").lower()
    return ("unknown column" in msg) or ("1054" in msg)


def _ensure_users_columns(conn, columns):
    required = [col for col in columns if col in USER_TABLE_ALTERS]
    if not required:
        return
    with conn.cursor() as cursor:
        for column in required:
            try:
                cursor.execute(USER_TABLE_ALTERS[column])
            except Exception as exc:
                msg = str(exc or "").lower()
                if "duplicate column" in msg or "1060" in msg:
                    continue
                raise
    conn.commit()


def _retry_after_users_column_fix(conn, columns, operation):
    try:
        return operation()
    except Exception as exc:
        if not _looks_like_missing_column(exc):
            raise
        conn.rollback()
        _ensure_users_columns(conn, columns)
        return operation()
