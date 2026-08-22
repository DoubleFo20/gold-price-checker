"""Generate a reproducible model-selection report; persist only with --apply."""

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

from database.connection import get_db_connection  # noqa: E402
from services.forecast_data import load_official_price_series  # noqa: E402
from services.forecast_models import evaluate_models  # noqa: E402


def persist_report(report: dict) -> None:
    champion = report["champion"]
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE forecast_model_metrics SET selected=0 WHERE selected=1")
            for metrics in report["models"]:
                selected = int(metrics["name"] == champion)
                cursor.execute(
                    """
                    INSERT INTO forecast_model_metrics (
                        model_name, model_version, selected, trained_through,
                        backtest_start, backtest_end, observations, metrics_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        selected=VALUES(selected), backtest_start=VALUES(backtest_start),
                        backtest_end=VALUES(backtest_end), observations=VALUES(observations),
                        metrics_json=VALUES(metrics_json), created_at=CURRENT_TIMESTAMP
                    """,
                    (
                        metrics["name"], report["model_version"], selected,
                        report["trained_through"], report["backtest_start"],
                        report["backtest_end"], report["observations"],
                        json.dumps(metrics, ensure_ascii=False),
                    ),
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    dates, values, quality = load_official_price_series()
    report = evaluate_models(values, dates)
    report["data_quality"] = quality
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.apply:
        persist_report(report)
        print("applied=true")
    else:
        print("dry_run=true (use --apply only after owner approval)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
