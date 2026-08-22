"""Create a schema-and-data logical backup using the application's DB driver."""
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


def _quoted_identifier(value: str) -> str:
    return "`" + value.replace("`", "``") + "`"


def create_backup(output: Path) -> dict:
    output.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db_connection()
    tables: list[str] = []
    rows_written = 0
    try:
        with conn.cursor() as cursor:
            cursor.execute("SHOW FULL TABLES WHERE Table_type='BASE TABLE'")
            tables = [next(iter(row.values())) for row in (cursor.fetchall() or [])]
            with output.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write("SET NAMES utf8mb4;\nSET FOREIGN_KEY_CHECKS=0;\n\n")
                for table in tables:
                    name = _quoted_identifier(table)
                    cursor.execute(f"SHOW CREATE TABLE {name}")
                    create_row = cursor.fetchone() or {}
                    create_sql = next(
                        value for key, value in create_row.items()
                        if str(key).lower().startswith("create ")
                    )
                    handle.write(f"DROP TABLE IF EXISTS {name};\n{create_sql};\n\n")
                    cursor.execute(f"SELECT * FROM {name}")
                    for row in cursor.fetchall() or []:
                        columns = ", ".join(_quoted_identifier(column) for column in row)
                        values = ", ".join(conn.escape(value) for value in row.values())
                        handle.write(f"INSERT INTO {name} ({columns}) VALUES ({values});\n")
                        rows_written += 1
                    handle.write("\n")
                handle.write("SET FOREIGN_KEY_CHECKS=1;\n")
    except Exception:
        output.unlink(missing_ok=True)
        raise
    finally:
        conn.close()
    return {"tables": len(tables), "rows": rows_written, "bytes": output.stat().st_size}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    result = create_backup(output)
    print(
        f"BACKUP_OK path={output} tables={result['tables']} "
        f"rows={result['rows']} bytes={result['bytes']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
