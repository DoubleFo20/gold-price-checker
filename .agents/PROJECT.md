# Project: Gold Price Checker (100% Production Readiness)

## Architecture
- **Backend**: Python 3.11 / Flask application factory (`api/app/create_app.py`) serving modular blueprints (`auth`, `forecast`, `alerts`, `prices`, `jobs`, `webhook`, `user`, `admin`).
- **Database**: PyMySQL with DBUtils connection pooling (`api/database/connection.py`) connecting to 17 canonical tables in MySQL/Aiven database.
- **Security & Middleware**: Flask-Limiter for IP/route rate limiting, secure password hashing (bcrypt), token-based sessions with immediate revocation on password reset.
- **Forecasting Engine**:
  - Agent A: Technical and statistical projections (ARIMA, Exponential Smoothing, moving averages).
  - Agent B: Macroeconomic & FX-adjusted projections (USD/THB GTA exchange rates, World Spot momentum, import parity).
  - Consensus & Debate Engine: Discrepancy detection (> 3%), algorithmic debate, weighted consensus, strict volatility-scaled Min-Max bounds ($Z \cdot \sigma \sqrt{h}$).
- **Notifications**: Multi-channel delivery engine (LINE Messaging API push & webhook, SMTP HTML email with `email_logs` delivery tracking, Web Push VAPID + hardened `sw.js`).
- **Frontend**: Standardized vanilla JavaScript SPA calling unified Flask endpoints (`/api/*`). Legacy PHP scripts deprecated.
- **Testing & CI/CD**: Pytest automated test suites covering all blueprints, backtesting validation ensuring MAPE < 5%, and automated Git synchronization to `origin/main`.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | DB Connection Pooling | Thread-safe connection pool using `DBUtils.pooled_db.PooledDB` in `api/database/connection.py` | M1 (DONE) | Survey 1, 3 |
| 2 | Password Reset Session Revocation | Immediately invalidate all active sessions in `sessions` table on password change | M1 (DONE) | Survey 1, 3 |
| 3 | Flask-Limiter Rate Limiting | Throttling on `/login`, `/register`, and sensitive auth endpoints | M1 (DONE) | Survey 1, 3 |
| 4 | Frontend API Standardization | Unify all API calls in `js/config.js` and `js/script.js` to `/api/*` and deprecate legacy PHP scripts | M1 (DONE) | Survey 1 |
| 5 | Email Verification & Password Reset Endpoints | Implement `/api/auth/forgot-password`, `/api/auth/reset-password`, `/api/auth/verify-email`, `/api/auth/resend-verify` in Flask | M2 | Survey 1, 3 |
| 6 | Responsive HTML Email Delivery & Logging | SMTP HTML email templates with persistent delivery logging in `email_logs` table | M2 | Survey 3 |
| 7 | Service Worker Push Hardening | Try-catch payload handling, window focus/reuse on notification click in `sw.js` | M2 | Survey 3 |
| 8 | Scheduled Morning Price Notification | Automated daily morning summary notification in `api/services/scheduler.py` | M2 | Survey 3 |
| 9 | 7-day & 30-day Forecast Horizons | Support 7-day and 30-day forward forecasts for both Thai Baht gold bar and World Spot gold | M3 | Survey 1, 2 |
| 10 | Dual-Agent Debate & Consensus | Agent A (technical) and Agent B (macro/FX) adversarial debate when discrepancy > 3% | M3 | Survey 2 |
| 11 | Strict Min-Max Safety Boundaries | Volatility-scaled dynamic safety bounds ($Z \cdot \sigma \sqrt{h}$) to prevent price drift/hallucinations | M3 | Survey 2 |
| 12 | Historical Data Exchange Rate Ingestion | Ingest `BahtPerUSD` from GTA historical feeds to populate `usd_thb` and reset freshness gate | M3 | Survey 2 |
| 13 | Pytest Suite Installation & Setup | Install `pytest` in `.venv` and update `requirements.txt` | M4 | Survey 1, 3 |
| 14 | Automated Test Suites | Unit and integration pytest suites for auth, alerts, security, and forecasting | M4 | Survey 3 |
| 15 | Backtesting Validation Engine | Automated walk-forward backtest verifying MAPE < 5% across 7-day and 30-day horizons | M4 | Survey 2 |
| 16 | Git Remote Synchronization | Stage, commit clean commits, and push to GitHub `DoubleFo20/gold-price-checker` on branch `main` | M5 | Survey 3 |
| 17 | Team Lead Zoro Supervisory Evaluation in Thai | Review all modules, metrics, and provide executive summary and operational report in Thai | M5 | ORIGINAL_REQUEST |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Backend Security & Database Architecture (Agent C) | Rate limiting, session revocation, DB connection pooling, legacy PHP deprecation | None | DONE |
| M2 | Notifications & Auth Flow Champion (Agent D) | Multi-channel alert dispatch, email verification & password reset flows, sw.js hardening | M1 | IN_PROGRESS |
| M3 | Forecasting Lead & Adversarial Specialist (Agent A & B) | 7-day & 30-day Thai & World Spot forecasts, dual-agent consensus debate, min-max bounds | M1 | PLANNED |
| M4 | QA Test & Backtesting Validation (Agent E) | Automated pytest suites, backtesting MAPE < 5% verification | M1, M2, M3 | PLANNED |
| M5 | GitHub Synchronization & Team Lead Zoro Report (Agent E & Zoro) | Git commit & push to origin/main, Zoro Thai executive report | M4 | PLANNED |

---

## Interface Contracts

### Auth ↔ Sessions
- `change_password(user_id, new_password)`:
  - Updates `users.password_hash`
  - Executes `DELETE FROM sessions WHERE user_id = %s`
  - Clears `session_token` cookie with `secure=_cookie_secure(), httponly=True, samesite="Lax"`
  - Returns `{ "success": True, "message": "..." }`

### Database Pool ↔ Application
- `get_db_connection()`:
  - Returns pooled connection from `DBUtils.pooled_db.PooledDB` using double-checked locking with `expected_key`
  - Supports context manager or standard `.cursor(pymysql.cursors.DictCursor)` and `.close()`

### Rate Limiting
- `limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])`
- `@limiter.limit("5 per minute")` on `/api/auth/login`, `/api/auth/register`, `/api/auth/forgot-password`

### Forecasting Engine ↔ API Routes
- `get_consensus_forecast(target="thai_bar"|"world_spot", horizon_days=7|30)`:
  - Output schema:
    ```json
    {
      "target": "thai_bar",
      "period": 7,
      "consensus_price": 43500.0,
      "min_price": 42800.0,
      "max_price": 44200.0,
      "agent_a_prediction": 43400.0,
      "agent_b_prediction": 43650.0,
      "discrepancy_pct": 0.57,
      "debate_triggered": false,
      "confidence_rating": "high",
      "consensus_weights": {"agent_a": 0.5, "agent_b": 0.5},
      "bounds_applied": true
    }
    ```

---

## Code Layout
- `api/app/create_app.py`: Flask application factory, blueprint registration, Flask-Limiter init
- `api/database/connection.py`: Pooled connection manager (`PooledDB`)
- `api/routes/auth_routes.py`: Auth endpoints, login, register, password change, reset, verify
- `api/routes/forecast_routes.py`: Forecast endpoints supporting 7 and 30-day horizons
- `api/services/forecast_service.py`: Forecasting coordination and model loader
- `api/services/forecast_debate.py`: Dual-agent consensus debate & min-max bounds engine
- `api/services/email_service.py`: SMTP delivery, HTML templates, and `email_logs` tracking
- `api/services/scheduler.py`: Scheduled jobs (price fetch, morning summaries, alert checks)
- `sw.js`: Service worker for web push
- `js/config.js`: Unified API endpoints configuration
- `tests/`: Automated pytest suites
