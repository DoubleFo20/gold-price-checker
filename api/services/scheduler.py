"""services/scheduler.py — Core scheduled job logic (no background thread)."""
import traceback
from datetime import datetime

from utils.helpers import to_float
from database.connection import get_db_connection, _ensure_users_columns
from services.gold_price import refresh_thai_cache, refresh_world_cache, thai_cache, world_cache
from services.notification import _deliver_price_alert
from services.email_service import send_forecast_result_email_smtp
from services.line_service import _line_push
from services.forecast_service import (
    ForecastUnavailableError,
    create_canonical_predictions,
    verify_canonical_predictions,
)
from services.forecast_data import OFFICIAL_SOURCE
from services.bot_exchange import fetch_daily_rate


def save_daily_price():
    """Save today's Thai gold price to price_cache table (runs once per day)."""
    try:

        thai_data = thai_cache.get("data")
        world_data = world_cache.get("data")
        if not thai_data or not thai_data.get("bar_sell"):
            return
        source_note = str(thai_data.get("source_note") or "Unknown").strip()
        is_official = source_note.upper().startswith("GTA") or "GOLD TRADERS ASSOCIATION" in source_note.upper()
        stored_source = OFFICIAL_SOURCE if is_official else source_note[:100]
        quality_status = "verified" if is_official else "unverified"
        today = datetime.now().date()
        # BOT is audit metadata only in model v1. Missing credentials/data must not
        # be replaced by a guessed exchange rate or block the gold-price refresh.
        try:
            usd_thb = fetch_daily_rate(today)
        except Exception as exc:
            usd_thb = None
            print(f"BOT reference rate unavailable: {type(exc).__name__}")
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, quality_status FROM price_cache WHERE date=%s", (today,))
                existing = cursor.fetchone()
                if existing and existing.get("quality_status") == "verified" and not is_official:
                    return
                if existing:
                    cursor.execute(
                        """
                        UPDATE price_cache SET
                            bar_buy=%s, bar_sell=%s, ornament_buy=%s, ornament_sell=%s,
                            world_usd=%s, world_thb=%s, usd_thb=COALESCE(%s, usd_thb), source=%s,
                            source_timestamp=NOW(), quality_status=%s
                        WHERE date=%s
                        """,
                        (
                            to_float(thai_data.get("bar_buy")),
                            to_float(thai_data.get("bar_sell")),
                            to_float(thai_data.get("ornament_buy")),
                            to_float(thai_data.get("ornament_sell")),
                            to_float(world_data.get("price_usd_per_ounce")) if world_data else None,
                            to_float(world_data.get("thb_per_baht_est")) if world_data else None,
                            usd_thb,
                            stored_source,
                            quality_status,
                            today,
                        ),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO price_cache (
                            date, bar_buy, bar_sell, ornament_buy, ornament_sell,
                            world_usd, world_thb, usd_thb, source, source_timestamp, quality_status
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
                        """,
                        (
                            today,
                            to_float(thai_data.get("bar_buy")),
                            to_float(thai_data.get("bar_sell")),
                            to_float(thai_data.get("ornament_buy")),
                            to_float(thai_data.get("ornament_sell")),
                            to_float(world_data.get("price_usd_per_ounce")) if world_data else None,
                            to_float(world_data.get("thb_per_baht_est")) if world_data else None,
                            usd_thb,
                            stored_source,
                            quality_status,
                        ),
                    )
            conn.commit()
            print(f"Saved daily price: {today} bar_sell={thai_data.get('bar_sell')}")
        finally:
            conn.close()
    except Exception as e:
        print(f"Failed to save daily price: {e}")


def run_scheduled_jobs_once():
    stats = {
        "ok": True, "errors": [], "checked_alerts": 0, "triggered_alerts": 0,
        "verified_forecasts": 0, "line_sent": 0, "push_sent": 0,
        "email_sent": 0, "notifications_saved": 0,
        "canonical_predictions": 0, "predictions_verified": 0,
        "forecast_ready": False,
    }

    try:
        thai_data = refresh_thai_cache()
    except Exception as e:
        stats["ok"] = False
        stats["errors"].append(f"thai_refresh_failed: {e}")
        thai_data = thai_cache.get("data") or {}
    try:
        world_data = refresh_world_cache()
    except Exception as e:
        stats["ok"] = False
        stats["errors"].append(f"world_refresh_failed: {e}")
        world_data = world_cache.get("data") or {}

    try:
        save_daily_price()
    except Exception as e:
        stats["ok"] = False
        stats["errors"].append(f"save_daily_price_failed: {e}")

    try:
        stats["predictions_verified"] = verify_canonical_predictions()
        canonical = create_canonical_predictions()
        stats["canonical_predictions"] = canonical["created"]
        stats["forecast_ready"] = True
    except ForecastUnavailableError:
        # Expected until the approved migration/import/backtest gate is complete.
        stats["forecast_ready"] = False
    except Exception as e:
        stats["forecast_ready"] = False
        stats["errors"].append(f"forecast_pipeline_failed: {type(e).__name__}")

    current_prices = {
        "bar": to_float(thai_data.get("bar_sell")) if thai_data else 0,
        "bar_buy": to_float(thai_data.get("bar_buy")) if thai_data else 0,
        "ornament": to_float(thai_data.get("ornament_sell")) if thai_data else 0,
        "world": to_float(world_data.get("price_usd_per_ounce")) if world_data else 0,
    }

    try:
        conn = get_db_connection()
    except Exception as e:
        stats["ok"] = False
        stats["errors"].append(f"db_connect_failed: {e}")
        stats["hint"] = "ตรวจสอบ DB_HOST/DB_USER/DB_PASS/DB_NAME"
        return stats

    try:
        with conn.cursor() as cursor:
            # ---- Price Alerts ----
            _ensure_users_columns(conn, ("line_user_id", "push_subscription"))
            alerts = []
            try:
                try:
                    cursor.execute(
                        """
                        SELECT pa.*, u.name, u.email, u.line_user_id, u.push_subscription,
                               COALESCE(pa.notify_email, u.email) AS receiver_email
                        FROM price_alerts pa
                        INNER JOIN users u ON u.id = pa.user_id
                        WHERE pa.triggered = 0
                        """
                    )
                except Exception:
                    cursor.execute(
                        """
                        SELECT pa.*, u.name, u.email,
                               COALESCE(pa.notify_email, u.email) AS receiver_email
                        FROM price_alerts pa
                        INNER JOIN users u ON u.id = pa.user_id
                        WHERE pa.triggered = 0
                        """
                    )
                alerts = cursor.fetchall() or []
            except Exception as e:
                stats["ok"] = False
                stats["errors"].append(f"alerts_query_failed: {e}")

            stats["checked_alerts"] = len(alerts)
            for alert in alerts:
                try:
                    target = float(alert.get("target_price") or 0)
                    ptype = alert.get("gold_type")
                    atype = alert.get("alert_type")
                    curr = current_prices.get(ptype, 0)
                    if not curr or not target:
                        continue
                    trigger = (atype == "above" and curr >= target) or (atype == "below" and curr <= target)
                    if not trigger:
                        continue
                    delivery = _deliver_price_alert(conn, alert, curr, stats=stats)
                    if delivery["notified"]:
                        cursor.execute(
                            "UPDATE price_alerts SET triggered=1, triggered_at=NOW() WHERE id=%s",
                            (alert["id"],),
                        )
                        stats["triggered_alerts"] += 1
                except Exception:
                    traceback.print_exc()

            # ---- Forecast Verification ----
            due_forecasts = []
            try:
                try:
                    cursor.execute(
                        """
                        SELECT sf.id, sf.user_id, sf.target_date, sf.max_price, sf.min_price,
                               sf.predicted_price, sf.model_name, sf.model_version,
                               u.name, u.email, u.line_user_id
                        FROM saved_forecasts sf
                        INNER JOIN users u ON u.id = sf.user_id
                        WHERE sf.verified_at IS NULL AND sf.target_date <= CURDATE()
                        ORDER BY sf.target_date ASC LIMIT 100
                        """
                    )
                except Exception:
                    cursor.execute(
                        """
                        SELECT sf.id, sf.user_id, sf.target_date, sf.max_price, sf.min_price,
                               u.name, u.email
                        FROM saved_forecasts sf
                        INNER JOIN users u ON u.id = sf.user_id
                        WHERE sf.verified_at IS NULL AND sf.target_date <= CURDATE()
                        ORDER BY sf.target_date ASC LIMIT 100
                        """
                    )
                due_forecasts = cursor.fetchall() or []
            except Exception as e:
                stats["ok"] = False
                stats["errors"].append(f"forecasts_query_failed: {e}")

            for row in due_forecasts:
                try:
                    target_date = row.get("target_date")
                    pred_max = float(row.get("max_price") or 0)
                    pred_min = float(row.get("min_price") or 0)
                    if pred_min > pred_max:
                        pred_min, pred_max = pred_max, pred_min

                    cursor.execute(
                        "SELECT bar_sell, bar_buy FROM price_cache WHERE date=%s ORDER BY created_at DESC LIMIT 1",
                        (target_date,),
                    )
                    cache_row = cursor.fetchone() or {}
                    actual_sell = to_float(cache_row.get("bar_sell"))
                    actual_buy = to_float(cache_row.get("bar_buy"))

                    if (actual_sell is None or actual_buy is None) and str(target_date) == datetime.now().date().isoformat():
                        actual_sell = actual_sell if actual_sell is not None else to_float(current_prices.get("bar"))
                        actual_buy = actual_buy if actual_buy is not None else to_float(current_prices.get("bar_buy"))

                    if actual_sell is None or actual_buy is None:
                        continue

                    # The production target is the official bar sell price.
                    is_accurate = pred_min <= actual_sell <= pred_max
                    predicted_price = to_float(row.get("predicted_price"))
                    try:
                        cursor.execute(
                            """
                            UPDATE saved_forecasts SET actual_max_price=%s, actual_min_price=%s,
                                actual_price=%s, absolute_error=%s, verified_at=NOW()
                            WHERE id=%s
                            """,
                            (
                                actual_sell, actual_sell, actual_sell,
                                abs(predicted_price - actual_sell) if predicted_price is not None else None,
                                row["id"],
                            ),
                        )
                    except Exception:
                        cursor.execute(
                            "UPDATE saved_forecasts SET actual_max_price=%s, actual_min_price=%s, verified_at=NOW() WHERE id=%s",
                            (actual_sell, actual_sell, row["id"]),
                        )
                    stats["verified_forecasts"] += 1

                    target_date_display = str(target_date)
                    try:
                        d = datetime.fromisoformat(str(target_date)[:10])
                        target_date_display = f"{d.day}/{d.month}/{d.year + 543}"
                    except Exception:
                        pass

                    line_sent = False
                    line_user_id = row.get("line_user_id")
                    if line_user_id:
                        status_text = "แม่นยำ ✅" if is_accurate else "ไม่แม่นยำ ❌"
                        msg = (
                            f"📊 ผลพยากรณ์ทองคำ ({target_date_display})\n"
                            f"- ผล: {status_text}\n"
                            f"- ช่วงพยากรณ์: ฿{pred_min:,.2f} - ฿{pred_max:,.2f}\n"
                            f"- ราคาจริง (ขายออก): ฿{actual_sell:,.2f}\n"
                            f"- ราคาจริง (รับซื้อ): ฿{actual_buy:,.2f}"
                        )
                        line_sent = _line_push(line_user_id, msg)
                        if line_sent:
                            stats["line_sent"] += 1

                    if not line_sent:
                        sent = send_forecast_result_email_smtp({
                            "email": row.get("email"), "name": row.get("name"),
                            "target_date_display": target_date_display,
                            "pred_min": pred_min, "pred_max": pred_max,
                            "actual_buy": actual_buy, "actual_sell": actual_sell,
                            "is_accurate": is_accurate,
                        })
                        if sent:
                            stats["email_sent"] += 1
                except Exception:
                    traceback.print_exc()

        conn.commit()
    finally:
        conn.close()

    return stats
