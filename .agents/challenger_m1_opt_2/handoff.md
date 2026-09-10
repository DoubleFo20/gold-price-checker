# Handoff Report: Milestone 1 - Statistical & Trajectory Adversarial Challenge

**Agent**: Empirical Challenger 2 (`challenger_m1_opt_2`)  
**Recipient**: Parent Orchestrator (`a0b2a93e-c5e3-4950-9ca4-725e4366883a`)  
**Date**: 2026-09-10  
**Handoff Type**: Hard Handoff (Challenge Complete)  
**Verdict**: **CHALLENGE_FAILED / REQUEST_CHANGES**

---

## 1. Observation

1. **Unhandled `TypeError` Crash on Missing/Null Metric Values in `api/services/forecast_service.py`**:
   - At line 106:
     ```python
     thirty = max(seven * 1.5, float(horizons.get("30", {}).get("absolute_error_p90", seven * 1.8)))
     ```
   - At line 112:
     ```python
     ninety = max(thirty * 1.3, float(horizons.get("90", {}).get("absolute_error_p90", thirty * 1.6)))
     ```
   - When a dictionary record has `"absolute_error_p90": null`, `dict.get()` returns `None`. Passing `None` to `float()` produces:
     `TypeError: float() argument must be a string or a real number, not 'NoneType'`
   - In `api/routes/forecast_routes.py:31-36`, only `ForecastUnavailableError` is caught. Any `TypeError` bubbles up as an unhandled HTTP 500 Internal Server Error.
   - Empirically reproduced and verified in `tests/test_m1_forecast_challenger.py:228-251` (`test_vulnerability_none_metric_triggers_unhandled_500_type_error`).

2. **Inverted Confidence Intervals ($Upper < Lower$) Under Non-Positive Metrics in `api/services/forecast_service.py`**:
   - At lines 94-100:
     ```python
     try:
         one = float(horizons["1"]["absolute_error_p90"])
         seven = max(one, float(horizons["7"]["absolute_error_p90"]))
     ```
   - If `absolute_error_p90` is negative (e.g. $-500.0$), `_interval_errors` returns negative errors `[-500.0, -415.0, ...]`.
   - At lines 431-432:
     ```python
     upper = [round(value + error, 2) for value, error in zip(bounded_predictions, errors)]
     lower = [round(max(0.0, value - error), 2) for value, error in zip(bounded_predictions, errors)]
     ```
   - For $value = 50000.0$: $upper = 49500.0$, $lower = 50500.0$. Thus $upper < lower$, violating the invariant $0 \le lower \le forecast \le upper$.
   - Empirically reproduced in `tests/test_m1_forecast_challenger.py:253-270` (`test_vulnerability_negative_error_metric_inverts_confidence_bounds`).

3. **Fallback & Cold-Start Latency Degradation (4s to 24s) in `api/services/forecast_service.py`**:
   - In `_get_resilient_price_series()` (lines 197-297), when the database is unreachable, it attempts 3 sequential DB connections that block on TCP socket timeouts.
   - Tier 4 then calls `refresh_thai_cache(force=False)` (line 280). When `thai_cache` is empty, it executes synchronous web scrapers across 7 external domains (`goldtraders.or.th`, `thongkam.com`, `goldprice.or.th`, etc.). Profiling logged:
     `_get_resilient_price_series: 20585.91ms`
   - In `_get_resilient_champion()` (lines 299-309), it calls `_load_champion()` on *every request* without an in-memory circuit breaker or failure cache. Profiling logged:
     `_get_resilient_champion: 4083.58ms`
   - Benchmark across 40 requests under fallback mode:
     `Mean: 4054.87ms | p95: 11865.41ms | Max: 17811.24ms`
   - Pure model computation latency is only `37.35ms`, proving the slowdown stems from synchronous network scraping and uncached DB connection timeouts.

4. **Global Rate Limiter Throttling Public Forecast API in `api/utils/limiter.py`**:
   - Lines 13-17:
     ```python
     limiter = Limiter(
         key_func=get_remote_address,
         default_limits=["200 per day", "50 per hour"],
         storage_uri=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
     )
     ```
   - `/api/forecast` is not exempt or given custom limits, causing users toggling periods or charts to be throttled with HTTP 429 ("คำขอมากเกินไป") after 50 hits in an hour.

5. **Test Suite Status**:
   - Challenger Test Suite (`pytest tests/test_m1_forecast_challenger.py`): **14 passed** in 20.35s.
   - Full Test Suite (`pytest tests/`): 324 passed out of 325. The only flaky failure was in `test_m1_challenger_edge_cases.py` due to global limiter state leaking across tests when run in a single process.

---

## 2. Logic Chain

1. **From Code Inspection to Unhandled 500 Defect**:
   - Line 106 and line 112 use `float(horizons.get(h, {}).get("absolute_error_p90", default))`.
   - In Python, `dict.get("key", default)` returns `None` if the key exists with value `None`.
   - `float(None)` raises `TypeError`.
   - `forecast_routes.py` has no `except Exception` handler, so Flask returns an unhandled 500 error.
   - Therefore, any database record with `None` in horizon metrics crashes the endpoint for users requesting 30d or 90d forecasts.

2. **From Unchecked Metric Inputs to Bound Inversion**:
   - Statistical errors must strictly be non-negative offsets.
   - `_interval_errors` performs no positivity check (`math.isfinite(x) and x > 0`).
   - When negative values pass into lines 431-432, adding a negative number decreases $upper$, while subtracting a negative number increases $lower$.
   - This inverts the confidence interval cone ($upper < lower$), breaking chart rendering and mathematical soundness.

3. **From Fallback Flow to Latency Bottleneck**:
   - Production failure fallback is meant to ensure high availability and responsiveness.
   - However, placing synchronous multi-domain web scraping (Tier 4) and repeated TCP socket connection attempts inside the HTTP request loop introduces up to 24 seconds of blocking latency.
   - On cloud hosting providers (Render, Heroku, Cloudflare), any HTTP response exceeding 10-15 seconds triggers an automatic HTTP 504 Gateway Timeout.
   - Therefore, the self-healing fallback in its current state risks trading a 503 for a 504 timeout during cold boots.

---

## 3. Caveats

1. **Holt ETS and Momentum Models**:
   - The underlying statistical algorithms (`forecast_ets` with damped trend, Agent B exponential attenuation $0.98^t$, dual-agent 3% debate switch, and min-max guardrails $\pm 2.5\%$, $\pm 7\%$, $\pm 12\%$, $\pm 18\%$) are mathematically sound and stable over 90 days.
2. **Review-Only Constraint**:
   - Per role constraints, this agent did not modify production code in `api/services/forecast_service.py` or `api/utils/limiter.py`. The fixes must be applied by the worker agent.

---

## 4. Conclusion

**Verdict: CHALLENGE_FAILED / REQUEST_CHANGES**

While Milestone 1 succeeded in restoring the 30-day and 90-day horizons and implementing the dual-agent guardrail architecture, the implementation must address the following required changes before production release:

1. **Fix `TypeError` in `_interval_errors`**: Wrap metric lookups for 30d and 90d in safe conversion logic so that `None`, non-numeric strings, or missing values safely fall back to scaled defaults without raising `TypeError`.
2. **Enforce Non-Negativity Floor on Errors**: Ensure `_interval_errors` enforces $error \ge last\_actual \times 0.001$, preventing inverted confidence bounds ($upper < lower$).
3. **Add Short-Lived Failure Cache for `_load_champion()`**: When DB connection fails, cache the failure state for 60 seconds so subsequent `/api/forecast` calls do not incur repeated 4-second socket timeouts.
4. **Exempt or Expand Rate Limits on `/api/forecast`**: Add `@limiter.limit("60 per minute")` or `@limiter.exempt` to the forecast route so users and charts are not blocked by the default 50/hour rate limit.

---

## 5. Verification Method

To independently verify these findings:

1. **Run Challenger Stress Suite**:
   ```powershell
   .venv\Scripts\python.exe -m pytest tests/test_m1_forecast_challenger.py -v
   ```
   *Expected outcome*: 14 passed, confirming the empirical proofs of vulnerabilities (`test_vulnerability_none_metric_triggers_unhandled_500_type_error` and `test_vulnerability_negative_error_metric_inverts_confidence_bounds`).

2. **Reproduce Unhandled 500 Crash**:
   ```powershell
   .venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'api'); from services.forecast_service import _interval_errors; _interval_errors({'horizons': {'30': {'absolute_error_p90': None}}}, 30)"
   ```
   *Expected outcome*: `TypeError: float() argument must be a string or a real number, not 'NoneType'`.

3. **Reproduce Inverted Bounds**:
   ```powershell
   .venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'api'); from services.forecast_service import _interval_errors; errs = _interval_errors({'horizons': {'1': {'absolute_error_p90': -500.0}, '7': {'absolute_error_p90': 10.0}}}, 7); print('Errors:', errs)"
   ```
   *Expected outcome*: Negative error offsets producing $upper < lower$.
