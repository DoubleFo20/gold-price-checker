"""Bank of Thailand USD/THB reference-rate client used for audit metadata."""
import os
from datetime import date

import requests

from utils.helpers import to_float


BOT_DAILY_REFERENCE_URL = (
    "https://gateway.api.bot.or.th/Stat-ReferenceRate/v2/DAILY_REF_RATE/get"
)


def _walk_json(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def parse_daily_rates(payload):
    """Return ``{YYYY-MM-DD: rate}`` across known BOT response envelopes."""
    results = {}
    date_keys = ("period", "date", "as_of_date", "observation_date")
    rate_keys = (
        "rate", "mid_rate", "reference_rate",
        "weighted_average_interbank_exchange_rate",
    )
    for item in _walk_json(payload):
        raw_date = next((item.get(key) for key in date_keys if item.get(key)), None)
        raw_rate = next((item.get(key) for key in rate_keys if item.get(key) is not None), None)
        if not raw_date or raw_rate is None:
            continue
        day = str(raw_date)[:10]
        rate = to_float(raw_rate)
        if len(day) == 10 and rate is not None and 10 <= rate <= 100:
            results[day] = rate
    return results


def fetch_daily_rates(start_date, end_date=None, session=requests):
    """Fetch official BOT reference rates; return an empty mapping if unconfigured."""
    token = (os.getenv("BOT_API_KEY") or "").strip()
    if not token:
        return {}
    start = start_date.isoformat() if isinstance(start_date, date) else str(start_date)
    end_value = end_date or start_date
    end = end_value.isoformat() if isinstance(end_value, date) else str(end_value)
    response = session.get(
        BOT_DAILY_REFERENCE_URL,
        headers={"Authorization": token},
        params={"start_period": start, "end_period": end},
        timeout=20,
    )
    response.raise_for_status()
    return parse_daily_rates(response.json())


def fetch_daily_rate(day=None, session=requests):
    """Fetch one official USD/THB rate, without substituting synthetic defaults."""
    target = day or date.today()
    return fetch_daily_rates(target, target, session=session).get(target.isoformat())
