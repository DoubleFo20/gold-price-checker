# Handoff Report: Self-Healing Production Forecast Fallback (R2)

**Agent:** Explorer 2 (`explorer_opt_2`)  
**Timestamp:** 2026-09-10T04:58:30+07:00  
**Handoff Type:** Hard (Task Complete)  
**Related Deliverable:** `d:\xampp\htdocs\gold-price-checker\.agents\explorer_opt_2\report.md`  

---

## 1. Observation

1. **Error Message and Exception Origin:**
   - In `api/services/forecast_service.py` (lines 27–33):
     ```python
     class ForecastUnavailableError(RuntimeError):
         """Raised when trustworthy production forecasting is not ready."""

         def __init__(self, reason: str, message: str = "ข้อมูลจริงยังไม่พร้อมสำหรับการพยากรณ์"):
             super().__init__(message)
             self.reason = reason
     ```
     The verbatim Thai string `"ข้อมูลจริงยังไม่พร้อมสำหรับการพยากรณ์"` is the default message of `ForecastUnavailableError`.

2. **Strict Data Qualification Thresholds:**
   - In `api/services/forecast_models.py` (line 23):
     `MIN_REQUIRED_OBSERVATIONS = 500`
   - In `api/services/forecast_data.py` (lines 49–57, 101–102):
     ```python
     ready = (
         len(rows) >= MIN_REQUIRED_OBSERVATIONS
         and duplicate_count == 0
         and null_count == 0
         and invalid_count == 0
         and continuity_gaps == 0
         and stale_days is not None
         and stale_days <= max_stale_days
     )
     ...
     if require_ready and not quality["ready"]:
         raise ValueError("Official forecast data is not ready.")
     ```
     If `price_cache` has $< 500$ rows, or a gap $> 10$ days, or staleness $> 4$ days, `load_official_price_series(require_ready=True)` raises `ValueError`, which `get_forecast()` converts to `ForecastUnavailableError("official_data_not_ready")`.

3. **Champion Model Dependency:**
   - In `api/services/forecast_service.py` (lines 53–54):
     ```python
     if not row:
         raise ForecastUnavailableError("champion_not_selected")
     ```
     If table `forecast_model_metrics` has no row where `selected=1`, `ForecastUnavailableError("champion_not_selected")` is raised.

4. **HTTP 503 Route Handler:**
   - In `api/routes/forecast_routes.py` (lines 28–35):
     ```python
     try:
         return jsonify(get_forecast(period, model_name, hist_days)), 200
     except ForecastUnavailableError as exc:
         return jsonify(
             error=str(exc),
             reason=exc.reason,
             forecast_ready=False,
         ), 503
     ```

5. **Client UI Alert Trigger:**
   - In `js/script.js` (lines 1621–1623, 1668–1671):
     ```javascript
     const r = await fetch(url);
     const j = await r.json();
     if (!r.ok) throw new Error(j?.error || r.statusText);
     ...
     } catch (e) {
         console.error('Forecast error:', e);
         alert('Error 1: ' + e.message + '\n' + e.stack);
     }
     ```
     Upon receiving HTTP 503, the frontend triggers a blocking browser popup: `"Error 1: ข้อมูลจริงยังไม่พร้อมสำหรับการพยากรณ์"`.

6. **Model Execution Verification:**
   - Verified that `forecast_ets` and `forecast_drift` in `api/services/forecast_models.py` execute without error on short series (5 and 30 observations) for both 7-day and 90-day projection horizons:
     - ETS 7-step on 5 points: `[50378.37, ..., 50843.70]`
     - Drift 7-step on 5 points: `[50437.50, ..., 50962.50]`
     - ETS 90-step on 30 points: `[50299.95, ..., 51012.55]` (damped trend strictly stable)

---

## 2. Logic Chain

1. **From Observation 1 & 4 to Root Cause:**
   The Thai error displayed to users directly originates from `ForecastUnavailableError` raised inside `get_forecast()` and handled in `forecast_routes.py` with HTTP 503 status.
2. **From Observation 2 & 3 to Production Fragility:**
   Any cloud or production deployment where `price_cache` has $< 500$ rows or where `forecast_model_metrics` lacks a pre-calculated champion record will unconditionally throw `ForecastUnavailableError`.
3. **From Observation 5 to User Impact:**
   The frontend `js/script.js` treats any non-2xx HTTP response as an exceptional condition and presents the raw error in a popup alert box, preventing the chart from rendering.
4. **From Observation 6 to Solution Feasibility:**
   Because Holt ETS (damped) and Momentum Drift execute deterministically and stably on small series ($N \ge 2$) and over long horizons (up to 90 days), an autonomous in-memory bootstrap model can take over whenever database prerequisites are unfulfilled.
5. **From Synthesis to Self-Healing Architecture:**
   By implementing a 4-tier data fallback (Official DB $\to$ Partial DB $\to$ Live Scraper $\to$ Static Anchor) and a 3-tier model selector (DB Champion $\to$ Auto-Promotion $\to$ In-Memory Bootstrap Ensemble), `/api/forecast` can guarantee an HTTP 200 OK response with strict min-max bounds (2.5% for 1d, 7% for 7d, 12% for 30d, 18% for 90d) under any environment condition.

---

## 3. Caveats

1. **Legacy Test Update Needed:**
   `tests/e2e/test_tier2_boundaries.py:470` (`test_b09_insufficient_historical_data_returns_503`) was written specifically to assert that $< 500$ rows returned HTTP 503. To satisfy the new acceptance criterion (*"When testing without 500 verified DB rows, the forecast endpoint still returns 200 OK with valid predictions instead of HTTP 503 error"*), this test must be updated by the implementer/QA engineer to assert 200 OK.
2. **Deployment Test Compatibility:**
   `tests/test_deployment.py:95` mocks `get_forecast` to raise `ForecastUnavailableError`. Keeping `ForecastUnavailableError` as an importable class and maintaining the `except ForecastUnavailableError` block in `forecast_routes.py` ensures this existing test remains 100% passing.

---

## 4. Conclusion

The production forecasting failure is completely diagnosed. The autonomous self-healing fallback mechanism designed in `report.md` resolves the issue by providing:
- Guaranteed HTTP 200 OK responses with full JSON schema (`labels`, `history`, `forecast`, `upper_bound`, `lower_bound`, `summary`, `dual_agent_consensus`, `evaluation`).
- Strict min-max guardrails: $\pm 2.5\%$ for 1 day, $\pm 7.0\%$ for 7 days, $\pm 12.0\%$ for 30 days, and $\pm 18.0\%$ for 90 days.
- Complete Dual-Agent Consensus Debate reconciliation whenever discrepancy exceeds 3.0%.
- Zero blocking browser alerts on the user interface.

Detailed code designs for `api/services/forecast_service.py` and `api/routes/forecast_routes.py` are documented in `d:\xampp\htdocs\gold-price-checker\.agents\explorer_opt_2\report.md`.

---

## 5. Verification Method

To independently verify this investigation:
1. **Inspect Report and Source Locations:**
   - Check `d:\xampp\htdocs\gold-price-checker\.agents\explorer_opt_2\report.md`.
   - Inspect `api/services/forecast_service.py` lines 27–54 and 150–165.
   - Inspect `api/services/forecast_data.py` lines 49–57 and 100–103.
   - Inspect `api/routes/forecast_routes.py` lines 20–35.
   - Inspect `js/script.js` lines 1621–1670.
2. **Execute Python Model Stability Test:**
   ```powershell
   .venv\Scripts\python.exe -c "
   import sys; sys.path.insert(0, 'api')
   from services.forecast_models import forecast_ets, forecast_drift
   values = [50000.0 + i*10.0 for i in range(30)]
   p90 = forecast_ets(values, 90)
   print('Length:', len(p90), 'Stable:', all(45000 < v < 55000 for v in p90))
   "
   ```
3. **Execute Existing Test Suite:**
   ```powershell
   .venv\Scripts\python.exe -m pytest tests/test_m2_m3_enhancements.py -k TestMilestone3
   ```
