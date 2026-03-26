"""database/connection.py — DB connection and schema-fix utilities."""
import os
import pymysql


USER_TABLE_ALTERS = {
    "name": "ALTER TABLE users ADD COLUMN name VARCHAR(100) NULL",
    "verification_token": "ALTER TABLE users ADD COLUMN verification_token VARCHAR(100) NULL",
    "line_user_id": "ALTER TABLE users ADD COLUMN line_user_id VARCHAR(100) NULL",
    "line_display_name": "ALTER TABLE users ADD COLUMN line_display_name VARCHAR(100) NULL",
    "push_subscription": "ALTER TABLE users ADD COLUMN push_subscription LONGTEXT NULL",
}


def get_db_connection():
    host = os.getenv("DB_HOST")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
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
        cursorclass=pymysql.cursors.DictCursor,
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
