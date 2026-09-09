# E2E Test Infrastructure Specification

## 1. Overview & Architectural Goals

The End-to-End (E2E) testing framework for the Gold Price Checker platform provides comprehensive, requirement-driven, opaque-box test coverage across all five system requirements (R1–R5) and the 17 features detailed in `PROJECT.md`.

The suite is engineered according to a **4-Tier Testing Methodology**:
- **Tier 1: Feature Coverage** (`tests/e2e/test_tier1_features.py`): 85 tests (5+ tests per feature across all 17 features) exercising primary functional flows and acceptance criteria.
- **Tier 2: Boundary & Corner Cases** (`tests/e2e/test_tier2_boundaries.py`): 85 tests (5+ tests per feature across all 17 features) covering extreme inputs, malformed payloads, unicode, boundary dates, and negative conditions.
- **Tier 3: Cross-Feature Combinations** (`tests/e2e/test_tier3_pairwise.py`): 15 tests verifying pairwise feature interactions (e.g., auth + forecasting, alerts + price updates, session revocation + token auth, rate limiting + brute-force prevention).
- **Tier 4: Real-World Scenarios** (`tests/e2e/test_tier4_scenarios.py`): 5 comprehensive end-to-end user workflows simulating complete multi-step journeys.

**Total E2E Tests: 190 tests.**

---

## 2. Test Execution & Environment

### 2.1 Prerequisites
- Python 3.11+
- Virtual environment at `.venv/` with all project dependencies and `pytest`:
  ```bash
  .venv\Scripts\python.exe -m pip install -r requirements.txt pytest
  ```

### 2.2 Execution Commands

To execute the entire E2E test suite:
```bash
.venv\Scripts\python.exe -m pytest tests/e2e/ -v
```

To execute individual tiers:
```bash
# Tier 1: Feature Coverage (85 tests)
.venv\Scripts\python.exe -m pytest tests/e2e/test_tier1_features.py -v

# Tier 2: Boundaries and Corner Cases (85 tests)
.venv\Scripts\python.exe -m pytest tests/e2e/test_tier2_boundaries.py -v

# Tier 3: Pairwise Combinations (15 tests)
.venv\Scripts\python.exe -m pytest tests/e2e/test_tier3_pairwise.py -v

# Tier 4: Real-World Scenarios (5 tests)
.venv\Scripts\python.exe -m pytest tests/e2e/test_tier4_scenarios.py -v
```

To run all project tests (E2E + existing unit/integration tests):
```bash
.venv\Scripts\python.exe -m pytest tests/ -v
```

---

## 3. In-Memory Database Simulation (`InMemoryDatabase`)

### 3.1 Design Principles
To guarantee deterministic execution, zero external service dependencies (no running MySQL daemon required), and rapid feedback (<60 seconds for 190 tests), the test suite uses an in-memory SQL mock engine implemented in `tests/e2e/conftest.py`.

### 3.2 Schema Emulation
The `InMemoryDatabase` emulates all 17 database tables defined across the platform:
- `users`: User profiles, bcrypt password hashes, verification status, roles (`user`, `admin`).
- `sessions`: Bearer tokens, user IDs, expiry dates, client IP, user-agent metadata.
- `price_alerts`: Alert triggers, target prices, condition types (`ABOVE`, `BELOW`), frequency (`ONCE`, `DAILY`, `REALTIME`), notification channels (`email`, `line`, `sms`, `push`).
- `price_cache`: Historical and live gold prices (Thai Gold Association buy/sell, spot gold prices, timestamps).
- `saved_forecasts`: User-saved AI forecasts, horizons, model types.
- `forecast_model_metrics`: Evaluation metrics (MAE, RMSE, MAPE, Directional Accuracy) per model type (`ensemble`, `linear_regression`, `arima`, `lstm`).
- `forecast_predictions`: Daily predicted prices with confidence bounds.
- `email_logs`, `audit_logs`, `push_subscriptions`, and related tables.

### 3.3 Mock Cursor & Query Parser (`MockCursor`)
`MockCursor` intercepts SQL queries issued by `pymysql` connections across all route and service handlers:
- **`SELECT`**: Supports column projections, `WHERE` clauses (equality, `AND`, `OR`, `LIKE`, `IN`, `IS NULL`), `ORDER BY` sorting, `LIMIT` offsets, and aggregate `COUNT(*)`.
- **`INSERT`**: Parses column lists and `VALUES`, automatically increments primary keys (`_auto_id`), and appends records.
- **`UPDATE`**: Parses `SET` expressions and conditionally modifies records matching `WHERE` clauses.
- **`DELETE`**: Conditionally removes records matching `WHERE` clauses.
- **`REPLACE INTO`**: Upserts records based on unique key constraints.

---

## 4. Test Isolation & Rate Limiting Strategy

### 4.1 State Isolation
Each test function receives fresh database state via the `mock_db` fixture. The database is re-initialized with standard seed records (e.g., standard test user `id=1`, admin user `id=2`, active session token `sess_valid_user1_token`).

### 4.2 Rate Limiting Handling
In production, the application enforces Flask-Limiter rate limits (e.g., 5 requests/minute for login, 10/minute for password reset). In batch test execution, repeated requests from the test client would trigger HTTP 429 throttling.

To reconcile strict testing with realistic rate-limit verification:
1. **Batch Test Suite**: In `tests/e2e/conftest.py`, `limiter.enabled = False` is set on the global app client. This allows high-throughput testing across Tiers 1–4 without false 429 failures.
2. **Dedicated Rate Limit Tests**: Tests verifying Feature 16 and rate-limiting enforcement instantiate isolated sub-applications with independent Limiter instances and custom IP keys, validating the 429 status code and JSON error payload structure.

---

## 5. Requirement & Feature Coverage Matrix

| Requirement | Features Covered | Test Files | Total Tests |
|---|---|---|---|
| **R1: Authentication & User Management** | F1 (Registration), F2 (Email Verification), F3 (Login & Sessions), F4 (Password Reset), F15 (Admin User Management) | `test_tier1_features.py`, `test_tier2_boundaries.py`, `test_tier3_pairwise.py`, `test_tier4_scenarios.py` | 55+ |
| **R2: Live Price Tracking & History** | F5 (Live Gold Price Scraping/API), F6 (Historical Data), F7 (Price Discrepancy & Gap Detection), F8 (CSV/JSON Export) | `test_tier1_features.py`, `test_tier2_boundaries.py`, `test_tier3_pairwise.py`, `test_tier4_scenarios.py` | 40+ |
| **R3: Multi-Channel Price Alerts** | F9 (Alert Creation & Rules), F10 (Email Notifications), F11 (LINE Notify Webhook), F12 (In-App & Push Notifications) | `test_tier1_features.py`, `test_tier2_boundaries.py`, `test_tier3_pairwise.py`, `test_tier4_scenarios.py` | 45+ |
| **R4: AI Price Forecasting Engine** | F13 (Forecasting Models), F14 (Forecast Evaluation Metrics), F17 (Quality Validation & Markdown Report) | `test_tier1_features.py`, `test_tier2_boundaries.py`, `test_tier3_pairwise.py`, `test_tier4_scenarios.py` | 35+ |
| **R5: Enterprise Reliability & Infrastructure** | F15 (Admin Dashboard), F16 (Git Operations & Pre-commit Quality Gates) | `test_tier1_features.py`, `test_tier2_boundaries.py`, `test_tier3_pairwise.py`, `test_tier4_scenarios.py` | 15+ |
| **Total** | **All 17 Features** | **4 Test Suites** | **190 Tests** |
