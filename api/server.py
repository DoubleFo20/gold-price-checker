# ===================== server.py =====================
# Entry point for Gunicorn: gunicorn api.server:app
# Minimal server that imports the application factory.

import os
from app.create_app import create_app

# Create Flask app via factory
app = create_app()

# Gunicorn alias – must be at module level
application = app

# Dev server entry point – background thread ONLY runs here
if __name__ == "__main__":
    import threading
    from scheduler.jobs import unified_background_alert_checker

    if (os.getenv("ENABLE_BACKGROUND_CHECKER", "true").strip().lower() in ("1", "true", "yes", "on")):
        threading.Thread(target=unified_background_alert_checker, daemon=True).start()
        print("✅ Background checker started (dev mode)")
    else:
        print("Background checker disabled (ENABLE_BACKGROUND_CHECKER=false)")

    port = int(os.getenv("PORT", "5000"))
    debug = (os.getenv("APP_DEBUG", "true").strip().lower() in ("1", "true", "yes", "on"))
    app.run(host="0.0.0.0", port=port, debug=debug)

# ===================== End of server.py =====================
