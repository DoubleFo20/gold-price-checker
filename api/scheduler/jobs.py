"""scheduler/jobs.py — Background thread workers (only run from __main__)."""
import time
import traceback
from services.scheduler import run_scheduled_jobs_once


def unified_background_alert_checker():
    """Background loop that runs jobs every 60 seconds.
    ONLY call this from if __name__ == '__main__' — never at import time.
    """
    while True:
        try:
            time.sleep(60)
            result = run_scheduled_jobs_once()
            if not result.get("ok", False):
                print(f"Background checker warning: {result}")
        except Exception as e:
            print(f"Error executing unified background cron: {e}")
