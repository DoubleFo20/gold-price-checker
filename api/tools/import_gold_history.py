"""Import official Gold Traders Association announcements into ``price_cache``.

Dry-run is the default.  ``--apply`` writes one verified row per announcement
date, using the final announcement of that date.  Database migration and this
apply mode require owner approval.
"""

from __future__ import annotations

import argparse
import calendar
import os
import sys
from datetime import date, datetime
from pathlib import Path

import requests
from dotenv import load_dotenv


API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

load_dotenv(API_ROOT / ".env")

from database.connection import get_db_connection  # noqa: E402
from services.forecast_data import OFFICIAL_SOURCE, assess_price_rows  # noqa: E402
from services.forecast_models import MIN_REQUIRED_OBSERVATIONS  # noqa: E402


SOURCE_URL = (
    "https://gtadmin.goldtraders.or.th/wp-admin/"
    "get_table_historical_gold_price_01_01.php"
)


def _month_ranges(start: date, end: date):
    cursor = start.replace(day=1)
    while cursor <= end:
        last_day = calendar.monthrange(cursor.year, cursor.month)[1]
        month_end = min(end, cursor.replace(day=last_day))
        yield max(start, cursor), month_end
        if cursor.month == 12:
            cursor = cursor.replace(year=cursor.year + 1, month=1)
        else:
            cursor = cursor.replace(month=cursor.month + 1)


def fetch_announcements(start: date, end: date, *, timeout: int = 30) -> list[dict]:
    rows: list[dict] = []
    session = requests.Session()
    session.headers["User-Agent"] = "GoldPriceChecker-Portfolio/1.0 (historical import)"
    for month_start, month_end in _month_ranges(start, end):
        response = session.get(
            SOURCE_URL,
            params={
                "dateStart": month_start.isoformat(),
                "dateEnd": month_end.isoformat(),
            },
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        month_rows = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(month_rows, list):
            raise ValueError(f"Unexpected official response for {month_start:%Y-%m}.")
        rows.extend(month_rows)
    return rows


def collapse_to_daily(announcements: list[dict]) -> list[dict]:
    latest_by_date: dict[str, dict] = {}
    for item in announcements:
        timestamp_text = str(item.get("AsTime") or "").strip()
        try:
            timestamp = datetime.fromisoformat(timestamp_text)
            bar_sell = float(item["BL_SellPrice"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Official announcement contains invalid required fields.") from exc
        if bar_sell <= 0:
            raise ValueError("Official announcement contains a non-positive sell price.")
        day = timestamp.date().isoformat()
        current = latest_by_date.get(day)
        if current is None or timestamp > current["source_timestamp"]:
            latest_by_date[day] = {
                "date": timestamp.date(),
                "bar_buy": float(item["BL_BuyPrice"]) if item.get("BL_BuyPrice") else None,
                "bar_sell": bar_sell,
                "ornament_buy": float(item["OM965_BuyPrice"]) if item.get("OM965_BuyPrice") else None,
                "ornament_sell": float(item["OM965_SellPrice"]) if item.get("OM965_SellPrice") else None,
                "world_usd": float(item["GoldSpot"]) if item.get("GoldSpot") else None,
                "source": OFFICIAL_SOURCE,
                "source_timestamp": timestamp,
                "quality_status": "verified",
            }
    return [latest_by_date[key] for key in sorted(latest_by_date)]


def apply_rows(rows: list[dict]) -> int:
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            for row in rows:
                cursor.execute(
                    """
                    INSERT INTO price_cache (
                        date, bar_buy, bar_sell, ornament_buy, ornament_sell,
                        world_usd, source, source_timestamp, quality_status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        bar_buy=VALUES(bar_buy), bar_sell=VALUES(bar_sell),
                        ornament_buy=VALUES(ornament_buy), ornament_sell=VALUES(ornament_sell),
                        world_usd=VALUES(world_usd),
                        source=VALUES(source), source_timestamp=VALUES(source_timestamp),
                        quality_status=VALUES(quality_status)
                    """,
                    (
                        row["date"], row["bar_buy"], row["bar_sell"],
                        row["ornament_buy"], row["ornament_sell"], row["world_usd"],
                        row["source"], row["source_timestamp"], row["quality_status"],
                    ),
                )
        conn.commit()
        return len(rows)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default=f"{date.today().year - 3}-01-01")
    parser.add_argument("--end", default=date.today().isoformat())
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    if start > end:
        parser.error("--start must not be after --end")

    daily = collapse_to_daily(fetch_announcements(start, end))
    quality = assess_price_rows(daily, today=end)
    print(
        f"source={OFFICIAL_SOURCE} rows={len(daily)} "
        f"first={quality['first_date']} latest={quality['latest_date']} "
        f"duplicates={quality['duplicate_dates']} invalid={quality['invalid_prices']} "
        f"continuity_gaps={quality['continuity_gaps']} ready={quality['ready']}"
    )
    if len(daily) < MIN_REQUIRED_OBSERVATIONS:
        raise SystemExit(
            f"Refusing import: {len(daily)} rows; at least {MIN_REQUIRED_OBSERVATIONS} are required."
        )
    if args.apply:
        print(f"applied_rows={apply_rows(daily)}")
    else:
        print("dry_run=true (use --apply only after backup and owner approval)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
