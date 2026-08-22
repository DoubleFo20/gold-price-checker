"""Dry-run-first importer for official BOT USD/THB audit metadata."""
import argparse
import json
import sys
from datetime import date
from pathlib import Path


API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from database.connection import get_db_connection  # noqa: E402
from services.bot_exchange import fetch_daily_rates  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", default=date.today().isoformat(), help="YYYY-MM-DD")
    parser.add_argument("--apply", action="store_true", help="Write rates to price_cache")
    args = parser.parse_args()

    rates = fetch_daily_rates(args.start, args.end)
    summary = {
        "mode": "apply" if args.apply else "dry-run",
        "rates": len(rates),
        "first": min(rates) if rates else None,
        "latest": max(rates) if rates else None,
    }
    if args.apply:
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                for day, rate in rates.items():
                    cursor.execute(
                        "UPDATE price_cache SET usd_thb=%s WHERE date=%s",
                        (rate, day),
                    )
            conn.commit()
        finally:
            conn.close()
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
