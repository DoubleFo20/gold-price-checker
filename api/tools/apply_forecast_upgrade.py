"""Apply and verify the approved idempotent forecast schema upgrade."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv


API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))
load_dotenv(API_ROOT / ".env")

from database.connection import get_db_connection  # noqa: E402


UPGRADE_SQL = API_ROOT / "sql" / "forecast_model_upgrade.sql"
EXPECTED_TABLES = {"forecast_model_metrics", "forecast_predictions"}
EXPECTED_PRICE_COLUMNS = {"usd_thb", "source", "source_timestamp", "quality_status"}
EXPECTED_SAVED_COLUMNS = {
    "prediction_id", "model_name", "model_version", "horizon_step",
    "predicted_price", "actual_price", "absolute_error", "direction_correct",
}
TABLE_COLUMNS = {
    "price_cache": {
        "usd_thb": "DECIMAL(10,4) NULL AFTER world_thb",
        "source": "VARCHAR(100) NULL AFTER usd_thb",
        "source_timestamp": "DATETIME NULL AFTER source",
        "quality_status": "VARCHAR(20) NOT NULL DEFAULT 'unverified' AFTER source_timestamp",
    },
    "saved_forecasts": {
        "prediction_id": "BIGINT UNSIGNED NULL AFTER actual_min_price",
        "model_name": "VARCHAR(100) NULL AFTER prediction_id",
        "model_version": "VARCHAR(50) NULL AFTER model_name",
        "horizon_step": "TINYINT UNSIGNED NULL AFTER model_version",
        "predicted_price": "DECIMAL(10,2) NULL AFTER horizon_step",
        "actual_price": "DECIMAL(10,2) NULL AFTER predicted_price",
        "absolute_error": "DECIMAL(10,2) NULL AFTER actual_price",
        "direction_correct": "TINYINT(1) NULL AFTER absolute_error",
    },
}


def _statements(sql: str):
    for chunk in sql.split(";"):
        statement = chunk.strip()
        if statement and not all(line.lstrip().startswith("--") for line in statement.splitlines()):
            yield statement


def verify_schema(conn) -> dict:
    with conn.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        tables = {next(iter(row.values())) for row in (cursor.fetchall() or [])}
        cursor.execute("SHOW COLUMNS FROM price_cache")
        price_columns = {row["Field"] for row in (cursor.fetchall() or [])}
        cursor.execute("SHOW COLUMNS FROM saved_forecasts")
        saved_columns = {row["Field"] for row in (cursor.fetchall() or [])}
    missing_tables = sorted(EXPECTED_TABLES - tables)
    missing_columns = sorted(EXPECTED_PRICE_COLUMNS - price_columns)
    missing_saved = sorted(EXPECTED_SAVED_COLUMNS - saved_columns)
    if missing_tables or missing_columns or missing_saved:
        raise RuntimeError(
            "Forecast schema verification failed: "
            f"tables={missing_tables}, price_columns={missing_columns}, "
            f"saved_columns={missing_saved}"
        )
    return {
        "tables": len(EXPECTED_TABLES),
        "columns": len(EXPECTED_PRICE_COLUMNS) + len(EXPECTED_SAVED_COLUMNS),
    }


def add_missing_columns(conn) -> int:
    added = 0
    with conn.cursor() as cursor:
        for table, definitions in TABLE_COLUMNS.items():
            cursor.execute(f"SHOW COLUMNS FROM `{table}`")
            existing = {row["Field"] for row in (cursor.fetchall() or [])}
            for column, definition in definitions.items():
                if column in existing:
                    continue
                cursor.execute(f"ALTER TABLE `{table}` ADD COLUMN `{column}` {definition}")
                added += 1
    return added


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        print("dry_run=true (pass --apply only after backup and owner approval)")
        return 0

    conn = get_db_connection()
    try:
        statements = list(_statements(UPGRADE_SQL.read_text(encoding="utf-8")))
        columns_added = add_missing_columns(conn)
        with conn.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
        conn.commit()
        verified = verify_schema(conn)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print(
        f"MIGRATION_OK statements={len(statements)} "
        f"columns_added={columns_added} tables={verified['tables']} "
        f"columns_verified={verified['columns']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
