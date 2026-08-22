"""Read and validate official daily Thai gold observations."""

from __future__ import annotations

import os
from datetime import date, datetime

from database.connection import get_db_connection
from services.forecast_models import MIN_REQUIRED_OBSERVATIONS


OFFICIAL_SOURCE = "Gold Traders Association"


def _to_iso(value) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()[:10]
    return str(value)[:10]


def assess_price_rows(rows: list[dict], *, today: date | None = None) -> dict:
    today = today or datetime.now().date()
    dates = [_to_iso(row.get("date")) for row in rows]
    prices = [row.get("bar_sell") for row in rows]
    duplicate_count = len(dates) - len(set(dates))
    null_count = sum(value is None for value in prices)
    invalid_count = 0
    for value in prices:
        try:
            # Wide plausibility limits catch unit/parse mistakes without acting as
            # a trading rule. They intentionally do not trim statistical outliers.
            invalid_count += not 5000 <= float(value) <= 500000
        except (TypeError, ValueError):
            invalid_count += 1
    unique_days = sorted({date.fromisoformat(value) for value in dates if len(value) == 10})
    day_gaps = [
        (current - previous).days
        for previous, current in zip(unique_days, unique_days[1:])
    ]
    max_gap_days = max(day_gaps, default=0)
    # Weekends and Thai public holidays are expected. A gap above ten calendar
    # days indicates a likely source/import outage and blocks production use.
    continuity_gaps = sum(gap > 10 for gap in day_gaps)
    latest = max(dates) if dates else None
    stale_days = None
    if latest:
        stale_days = (today - date.fromisoformat(latest)).days
    max_stale_days = int(os.getenv("FORECAST_MAX_STALE_DAYS", "4"))
    ready = (
        len(rows) >= MIN_REQUIRED_OBSERVATIONS
        and duplicate_count == 0
        and null_count == 0
        and invalid_count == 0
        and continuity_gaps == 0
        and stale_days is not None
        and stale_days <= max_stale_days
    )
    return {
        "ready": ready,
        "observations": len(rows),
        "required_observations": MIN_REQUIRED_OBSERVATIONS,
        "first_date": min(dates) if dates else None,
        "latest_date": latest,
        "stale_days": stale_days,
        "max_stale_days": max_stale_days,
        "duplicate_dates": duplicate_count,
        "null_prices": null_count,
        "invalid_prices": invalid_count,
        "max_gap_days": max_gap_days,
        "continuity_gaps": continuity_gaps,
        "source": OFFICIAL_SOURCE,
    }


def load_official_price_series(limit: int = 1000, *, require_ready: bool = True) -> tuple[list[str], list[float], dict]:
    """Load the latest rows, then return them in chronological order."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT date, bar_sell, source, source_timestamp, quality_status
                FROM (
                    SELECT date, bar_sell, source, source_timestamp, quality_status
                    FROM price_cache
                    WHERE bar_sell IS NOT NULL
                      AND source = %s
                      AND quality_status = 'verified'
                    ORDER BY date DESC
                    LIMIT %s
                ) recent
                ORDER BY date ASC
                """,
                (OFFICIAL_SOURCE, int(limit)),
            )
            rows = cursor.fetchall() or []
    finally:
        conn.close()

    quality = assess_price_rows(rows)
    if require_ready and not quality["ready"]:
        raise ValueError("Official forecast data is not ready.")
    return (
        [_to_iso(row["date"]) for row in rows],
        [float(row["bar_sell"]) for row in rows],
        quality,
    )
