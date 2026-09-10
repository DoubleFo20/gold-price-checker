# Project: Forecast Engine Restoration & Admin Chart Optimization

## Architecture
- **Backend**: Python 3.11 / Flask application factory (`api/app/create_app.py`) serving modular blueprints (`forecast`, `prices`, `auth`, `alerts`, `admin`).
- **Forecasting Engine (Self-Healing & Dual-Agent Consensus)**:
  - Supports 1, 7, 30, and 90-day projection intervals.
  - Multi-tier data fallback pipeline: Official DB (>=500 rows) -> Partial DB (<500 rows) -> Live Market Scraper Anchor -> Static Deterministic Anchor.
  - Model pipeline: Database Champion -> Dynamic Auto-Promotion -> In-Memory Bootstrap Ensemble (Holt ETS damped + Momentum Drift + Dual-Agent Debate).
  - Strict bounded safety guardrails: max ±2.5% for 1d, ±7% for 7d, ±12% for 30d, ±18% for 90d.
  - Guaranteed HTTP 200 OK responses with full evaluation metadata, eliminating "ข้อมูลจริงยังไม่พร้อมสำหรับการพยากรณ์".
- **Historical Data Pipeline & Admin Chart**:
  - Direct local `price_cache` queries with zero-network deterministic daily baseline fallback anchored on `bar_sell` in 50-THB steps.
  - Completely decouples `/api/historical` from blocking `yfinance` network calls, achieving <10ms response times.
  - Fixes 10x spot price calculation bug and -12% hockey-stick distortion.
  - Admin Chart.js optimization with `maxTicksLimit: 5`, `grace: '8%'`, Thai short date labels (`"10 ก.ย."`), and `.chart-wrapper` responsive container.
- **Testing & Supervisory**:
  - Full automated pytest suites verifying endpoints, boundaries, and performance.
  - Executive supervisory sign-off and detailed milestone conclusions in Thai by Team Lead Zoro.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Restore 30d & 90d UI Options | Add 30-day and 90-day options to `#forecast-period` dropdown in `components/6-forecast.html` | M1 | Survey 1, ORIGINAL_REQUEST R1 |
| 2 | Expand Supported Periods | Expand `SUPPORTED_PERIODS` to `(1, 7, 30, 90)` in `api/routes/forecast_routes.py` and `api/services/forecast_service.py` | M1 | Survey 1, ORIGINAL_REQUEST R1 |
| 3 | Extended Error Bounds Interpolation | 3-segment piecewise-linear error bounds (`_interval_errors`) with sqrt(t) scaling for 90d | M1 | Survey 1, ORIGINAL_REQUEST R1 |
| 4 | 90-Day Evaluation Payload | Implement 90-day evaluation fallback in `_evaluation_payload` to supply valid UI accuracy metrics | M1 | Survey 1, ORIGINAL_REQUEST R1 |
| 5 | 4-Tier Self-Healing Data Pipeline | Fallback sequence (Official DB -> Partial DB -> Live Scraper -> Static Anchor) guaranteeing data availability | M1 | Survey 2, ORIGINAL_REQUEST R2 |
| 6 | In-Memory Bootstrap & Guardrails | Holt ETS damped + Momentum Drift ensemble guaranteeing 200 OK and bounds (2.5% 1d, 7% 7d, 12% 30d, 18% 90d) | M1 | Survey 2, ORIGINAL_REQUEST R2 |
| 7 | Eliminate yfinance from /api/historical | Cut out synchronous external Yahoo Finance network calls, dropping latency from 12s to <10ms | M2 | Survey 3, ORIGINAL_REQUEST R3 |
| 8 | Fast Local Price Cache & Live Baseline | Serve real Thai gold data from `price_cache` with deterministic live market price baseline fallback | M2 | Survey 3, ORIGINAL_REQUEST R3 |
| 9 | Fix Historical Data Bugs | Fix 10x world gold spot calculation bug and -12% synthetic hockey-stick jump in `api/services/historical.py` | M2 | Survey 3, ORIGINAL_REQUEST R3 |
| 10 | Admin 7-Day Chart Crisp Rendering | Set `maxTicksLimit: 5`, `grace: '8%'`, Thai short dates, and wrap `<canvas>` inside `.chart-wrapper` | M2 | Survey 3, ORIGINAL_REQUEST R3 |
| 11 | Comprehensive Pytest Verification | Execute full automated test suite (`pytest tests/`) ensuring zero regressions | M3 | ORIGINAL_REQUEST R4 |
| 12 | Team Lead Zoro Thai Supervisory Report | Detailed milestone reports, model stability verification, and executive conclusion in Thai | M3 | ORIGINAL_REQUEST R5 |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Forecast Engine Restoration & Horizons (Agent A) | F1, F2, F3, F4, F5, F6: UI dropdown, 30d/90d horizons, self-healing fallback, bounded bootstrap, guaranteed 200 OK | None | IN_PROGRESS |
| M2 | Admin Chart Performance & Real Baseline Data (Agent B) | F7, F8, F9, F10: Eliminate yfinance, <100ms response, fix 10x bug, crisp Admin 7-day chart rendering | None | PLANNED |
| M3 | E2E Verification & Zoro Thai Sign-off (Agent E & Zoro) | F11, F12: Automated pytest suite validation and Team Lead Zoro comprehensive Thai supervisory sign-off | M1, M2 | PLANNED |

---

## Interface Contracts

### Forecast API Contract
- Route: `GET /api/forecast?period={1|7|30|90}&model={optional}&hist_days={optional}`
- Status: Guaranteed `200 OK`
- Output Schema:
  ```json
  {
    "target": "thai_bar",
    "period": 90,
    "model": "champion_or_bootstrap",
    "labels": ["..."],
    "history": [50400.0, "..."],
    "forecast": [50500.0, "..."],
    "upper_bound": [51200.0, "..."],
    "lower_bound": [49800.0, "..."],
    "summary": {
      "current_price": 50400.0,
      "forecast_price": 50500.0,
      "change": 100.0,
      "change_pct": 0.20,
      "direction": "up"
    },
    "dual_agent_consensus": {
      "consensus_price": 50500.0,
      "agent_a_prediction": 50480.0,
      "agent_b_prediction": 50520.0,
      "discrepancy_pct": 0.08,
      "bounds_applied": true
    },
    "evaluation": {
      "mae": 150.0,
      "rmse": 180.0,
      "mape": 0.35,
      "direction_accuracy": 72.0
    }
  }
  ```

### Historical Data API Contract
- Route: `GET /api/historical?days={days}`
- Status: Guaranteed `200 OK` (latency < 100ms)
- Output Schema:
  ```json
  {
    "days": 7,
    "source": "Gold Traders Association" | "Live Market Baseline",
    "labels": ["4 ก.ย.", "5 ก.ย.", "6 ก.ย.", "7 ก.ย.", "8 ก.ย.", "9 ก.ย.", "10 ก.ย."],
    "values": [50350.0, 50400.0, 50400.0, 50450.0, 50500.0, 50450.0, 50400.0],
    "world_gold_usd": [2550.0, 2552.0, 2552.0, 2555.0, 2558.0, 2556.0, 2554.0]
  }
  ```

---

## Code Layout & Write Ownership
- **Milestone 1 (Agent A)**:
  - `components/6-forecast.html` (Exclusive write)
  - `api/routes/forecast_routes.py` (Exclusive write)
  - `api/services/forecast_service.py` (Exclusive write)
  - `tests/e2e/test_tier2_boundaries.py` (Exclusive write for test_b09 update)
- **Milestone 2 (Agent B)**:
  - `api/services/historical.py` (Exclusive write)
  - `api/routes/prices.py` (Exclusive write)
  - `admin/js/admin.js` (Exclusive write)
  - `admin/css/admin.css` (Exclusive write)
  - `admin/index.html` (Exclusive write)
  - `tests/test_historical_api.py` (Exclusive write)
