# Adversarial Challenge Report: Milestone 1 - Forecast Engine Restoration & Horizons

**Agent**: Empirical Challenger 2 (`challenger_m1_opt_2`)  
**Role**: Critic, Specialist (Time-Series Forecasting & Statistical Invariants)  
**Date**: 2026-09-10  
**Target Work Product**: Milestone 1 implementation by `worker_m1_opt_2` (`api/services/forecast_service.py`, `api/routes/forecast_routes.py`, `components/6-forecast.html`)  
**Verdict**: **CHALLENGE_FAILED / REQUEST_CHANGES**

---

## Challenge Summary

**Overall risk assessment**: **HIGH**  
While core statistical models (Holt ETS damped trend, Agent B momentum damping, dual-agent consensus weighting, and strict min-max guardrails) performed robustly across synthetic regimes, deep empirical stress-testing identified two critical statistical/code defects and one major performance architectural bottleneck:

1. **[CRITICAL] Unhandled `TypeError` (HTTP 500) on 30d/90d Error Metrics**: If `metrics["horizons"]["30"]["absolute_error_p90"]` or `metrics["horizons"]["90"]["absolute_error_p90"]` is `None` (common in partial DB records or uncalibrated models), `float(None)` raises an unhandled `TypeError`. Because `forecast_routes.py` only catches `ForecastUnavailableError`, this triggers an unhandled HTTP 500 Internal Server Error, displaying alert popups on the frontend.
2. **[HIGH] Statistical Inversion of Confidence Bounds ($Upper < Lower$)**: In `_interval_errors`, raw `absolute_error_p90` values from the DB are not validated against non-positivity. If a corrupted or negative error metric (e.g. $-500.0$) is passed, the error becomes negative, causing $upper\_bound < lower\_bound$ and completely inverting the confidence cone.
3. **[HIGH] Cold-Start / Fallback Latency Bottleneck (4s - 24s)**: When the database is offline or in cold start, `_get_resilient_price_series()` attempts 3 sequential DB connections that block on TCP timeout, followed by synchronous scraping across 7 public internet websites (taking ~20.5 seconds). Furthermore, `_get_resilient_champion()` attempts `_load_champion()` on *every single request* without a circuit breaker or cache, adding ~4.08 seconds of TCP socket timeout latency per hit. Average fallback latency is 4,054 ms (p95: 11,865 ms, max: 17,811 ms), creating severe vulnerability to HTTP 504 Gateway Timeouts on Render/Heroku.
4. **[MEDIUM] Global Rate Limiter Throttles Public Forecast API (50/hr)**: `utils/limiter.py` sets a global default limit of `50 per hour` across the entire application without exempting `/api/forecast`. A user toggling periods (1d, 7d, 30d, 90d) or viewing charts in rapid succession gets throttled with HTTP 429 Too Many Requests.

---

## Challenges

### [Critical] Challenge 1: Unhandled `TypeError` Crash in 30-Day and 90-Day Error Spline

- **Assumption challenged**: The worker assumed `horizons.get("30", {}).get("absolute_error_p90", seven * 1.8)` will always return a valid float or fall back to `seven * 1.8`.
- **Attack scenario**: If the database record contains `"absolute_error_p90": null` in the JSON dictionary for horizon 30 or 90, `dict.get("absolute_error_p90", default)` returns `None` (because the key exists), and `float(None)` raises `TypeError: float() argument must be a string or a real number, not 'NoneType'`.
- **Blast radius**:
  - `api/services/forecast_service.py:106` and line `112` crash.
  - `api/routes/forecast_routes.py:30` does not catch `TypeError`.
  - The endpoint crashes with HTTP 500 Internal Server Error.
  - On the frontend (`js/script.js:1671`), `alert('Error 1: ...')` fires and breaks the UI.
- **Empirical Proof**:
  Verified via `tests/test_m1_forecast_challenger.py::ChallengerAdversarialBugReproductions::test_vulnerability_none_metric_triggers_unhandled_500_type_error`:
  ```python
  bad_metrics_30 = {"horizons": {"1": {"absolute_error_p90": 200.0}, "7": {"absolute_error_p90": 500.0}, "30": {"absolute_error_p90": None}}}
  # Raises TypeError: float() argument must be a string or a real number, not 'NoneType'
  ```
- **Recommended Mitigation**:
  In `_interval_errors`, wrap horizon metric extraction in a safe numeric helper:
  ```python
  def _safe_error(h_dict: dict, default: float) -> float:
      val = (h_dict or {}).get("absolute_error_p90")
      try:
          f_val = float(val)
          return f_val if math.isfinite(f_val) and f_val > 0 else default
      except (TypeError, ValueError):
          return default
  ```

---

### [High] Challenge 2: Non-Positive Metrics Invert Confidence Bounds ($Upper < Lower$)

- **Assumption challenged**: The worker assumed `metrics["horizons"][h]["absolute_error_p90"]` is always strictly positive.
- **Attack scenario**: If a negative number is stored or generated during backtesting calibration (e.g. $-500.0$), `_interval_errors` propagates negative error values across the trajectory (e.g. `[-500.0, -415.0, -330.0, ...]`).
- **Blast radius**:
  - At line 431-432:
    `upper = round(value + error, 2)` -> $50000 + (-500) = 49500.0$
    `lower = round(max(0.0, value - error), 2)` -> $\max(0.0, 50000 - (-500)) = 50500.0$
  - Result: $upper < lower$, directly violating the invariant $0 \le lower \le forecast \le upper$.
- **Empirical Proof**:
  Verified via `tests/test_m1_forecast_challenger.py::ChallengerAdversarialBugReproductions::test_vulnerability_negative_error_metric_inverts_confidence_bounds`:
  ```
  Step 1 error: -500.0 -> upper = 49500.0, lower = 50500.0 (upper < lower)
  ```
- **Recommended Mitigation**:
  Enforce a hard floor in `_interval_errors`:
  ```python
  one = max(round(last_actual * 0.001, 2), float(horizons["1"]["absolute_error_p90"]))
  seven = max(one, float(horizons["7"]["absolute_error_p90"]))
  ```

---

### [High] Challenge 3: Cold-Start & DB Outage Fallback Latency (4s to 24s)

- **Assumption challenged**: The worker claimed the fallback bootstrap provides a snappy, seamless experience when DB rows are insufficient or unavailable.
- **Attack scenario**: On cloud deployment (Render cold boot) or when MySQL is unreachable:
  1. `_get_resilient_price_series()` attempts `load_official_price_series(require_ready=True)` -> blocks on socket timeout.
  2. It attempts `load_official_price_series(require_ready=False)` -> blocks on socket timeout.
  3. It attempts `get_db_connection()` -> blocks on socket timeout.
  4. Tier 4 calls `refresh_thai_cache(force=False)`. If cache is empty, it synchronously launches 7 external HTTP web scrapers sequentially/concurrently across the internet.
  5. `_get_resilient_champion()` calls `_load_champion()` which calls `get_db_connection()` *again* on every single forecast request.
- **Blast radius**:
  - Cold-start request takes **20.58 seconds** for `_get_resilient_price_series` + **4.08 seconds** for `_get_resilient_champion` = **24.66 seconds** total!
  - Warm fallback requests still take **4.08 seconds** because `_load_champion()` has no circuit breaker or failure cache.
  - Cloud platforms (Render, Heroku, Cloudflare) terminate connections with HTTP 504 Gateway Timeout after 10-15 seconds.
- **Empirical Proof**:
  Direct profiling output from `api/services/forecast_service.py`:
  ```
  Attempting goldtraders.or.th (HTML)...
  Attempting thongkam.com...
  Attempting goldprice.or.th API...
  Attempting huasengheng.com API...
  Attempting intergold.co.th (AJAX)...
  Attempting Finnomena API...
  Attempting ecggoldshop.com...
  Success from thongkam.com.
  Success from intergold.co.th.
  _get_resilient_price_series: 20585.91ms
  _get_resilient_champion: 4083.58ms
  ```
  Benchmark latencies under fallback:
  `Mean: 4054.87ms | p95: 11865.41ms | Max: 17811.24ms`
  (Whereas isolated model computation is only **37.35ms**).
- **Recommended Mitigation**:
  1. Implement a short-lived in-memory circuit breaker or failure cache for `_load_champion()` (e.g., if DB connection fails, do not re-attempt for 60 seconds).
  2. Avoid synchronous live web scraping inside the request-response cycle of `/api/forecast`; use stale cache or the deterministic anchor immediately if cache is empty.

---

### [Medium] Challenge 4: Global Rate Limiting Throttles Public Forecast API

- **Assumption challenged**: Rate limiting was assumed to only target auth routes.
- **Attack scenario**: `utils/limiter.py` configures `default_limits=["200 per day", "50 per hour"]`. Since `forecast_bp` does not declare `@limiter.exempt` or custom limits, all forecast requests consume the global 50/hour quota.
- **Blast radius**:
  - An active user clicking between 1d, 7d, 30d, and 90d periods gets blocked with HTTP 429 after 50 clicks.
  - Automated integration tests and health check probes get throttled.
- **Empirical Proof**:
  Verified in test run where consecutive parameter tests returned HTTP 429 ("คำขอมากเกินไป") instead of 400.
- **Recommended Mitigation**:
  Exempt `/api/forecast` from the strict 50/hour default or assign a high-volume limit:
  ```python
  @forecast_bp.route("/api/forecast", methods=["GET"])
  @limiter.limit("60 per minute")
  def forecast(): ...
  ```

---

## Stress Test Results

| Scenario | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|
| Holt ETS 90-Day Trajectory (5 regimes: steady, bull, bear, shock, flat) | Finite, positive, damped growth | Finite, positive, damped (no divergence) | **PASS** |
| Agent B Momentum Damping | Attenuation via $0.98^t$, marginal change decays | Smoothly dampens; marginal change at step 90 < step 1 | **PASS** |
| Dual-Agent Debate Oracle | Diff > 3% triggers debate (60:40); <= 3% triggers agreement (70:30) | Thresholds and verdicts match specification exactly | **PASS** |
| Guardrail Enforcement (1d: 2.5%, 7d: 7%, 30d: 12%, 90d: 18%) | Clamps extreme $\pm 50\%$ model drifts | Predictions strictly bounded within $[\text{min}, \text{max}]$ | **PASS** |
| Confidence Cone Monotonicity (clean metrics) | $W(t+1) \ge W(t)$ across all 90 steps | Non-decreasing width across all 4 horizons | **PASS** |
| Error Spline Continuity | Smooth transitions at $t=7 \to 8$ and $t=30 \to 31$ | $\Delta_{7 \to 8} \ge 0$, $\Delta_{30 \to 31} \ge 0$ | **PASS** |
| Sparse DB Bootstrap ($N = 3$) | Pads history to $\ge 30$ points, returns 200 OK | Pads to 30 points, forecast returns 200 OK | **PASS** |
| Market Shocks (50% crash, 100% spike, flatline) | Engine does not crash, guardrails hold | Models adapt, predictions clamped safely | **PASS** |
| Adversarial Metric: `None` in 30d/90d `absolute_error_p90` | Safe fallback to default scaling | Uncaught `TypeError` -> HTTP 500 | **FAIL** |
| Adversarial Metric: Negative `absolute_error_p90` | Hard floor prevents cone inversion | Negative error -> $Upper < Lower$ | **FAIL** |
| Fallback Response Latency (DB down) | Snappy (< 200ms) | 4,054ms mean, 24,660ms cold start | **FAIL** |
| Request Volume on `/api/forecast` (> 50/hour) | High-volume read availability | Blocked by HTTP 429 rate limit | **FAIL** |

---

## Unchallenged Areas

- **SMTP Email Delivery (`/api/forecast/send-email`)**: Out of scope for Milestone 1 statistical forecasting engine (part of Agent D notification hardening in Milestone 2/3).
- **Admin Dashboard Historical Chart Rendering**: Assigned exclusively to Milestone 2 (Agent B).
