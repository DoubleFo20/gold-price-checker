"""Smoke-check the persisted forecast release; write predictions only with --apply."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv


API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))
load_dotenv(API_ROOT / ".env")

from services.forecast_service import create_canonical_predictions, get_forecast  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    one = get_forecast(1)
    seven = get_forecast(7)
    result = {
        "model": seven["model"],
        "model_version": seven["model_version"],
        "trained_through": seven["trained_through"],
        "observations": seven["data_quality"]["observations"],
        "horizon_1": one["evaluation"],
        "horizon_7": seven["evaluation"],
        "intervals_valid": all(
            lower <= predicted <= upper
            for lower, predicted, upper in zip(
                seven["lower_bound"], seven["forecast"], seven["upper_bound"]
            )
        ),
    }
    if args.apply:
        result["canonical"] = create_canonical_predictions()
    else:
        result["canonical"] = {"created": 0, "dry_run": True}
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
