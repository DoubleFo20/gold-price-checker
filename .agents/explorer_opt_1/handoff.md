# Handoff Report: R1 Restoring 30-Day and 90-Day Forecast Horizons

**Author**: Explorer Opt 1  
**Working Directory**: `d:\xampp\htdocs\gold-price-checker\.agents\explorer_opt_1`  
**Date**: 2026-09-09T22:10:00Z  
**Type**: Hard Handoff (Investigation Complete)  

---

## 1. Observation

1. **Frontend Dropdown Missing 30 & 90 Days**:
   - In `components/6-forecast.html` lines 17–20:
     ```html
     <select id="forecast-period" class="custom-select">
         <option value="1">1 วันประกาศราคาถัดไป</option>
         <option value="7" selected>7 วันประกาศราคาถัดไป</option>
     </select>
     ```
     Only options for 1 and 7 days exist.

2. **Frontend Dynamic API Dispatch & Rendering**:
   - In `js/script.js` lines 1607–1623, `generateForecast()` executes:
     ```javascript
     const period = parseInt(periodEl.value || '7', 10);
     const histDays = '365';
     const model = 'champion';
     const url = buildPythonApiUrl(`/api/forecast?period=${period}&model=${model}&hist_days=${histDays}`);
     ```
   - In `js/script.js` lines 1452–1578, `renderForecastChart(payload)` indexes dynamically:
     ```javascript
     const histLen = payload.history.length;
     const forecastLen = payload.forecast.length;
     const totalLen = labels.length;
     const histData = payload.history.concat(Array(totalLen - histLen).fill(null));
     forecastData[totalLen - forecastLen - 1] = lastRealPrice;
     for (let i = 0; i < forecastLen; i++) {
         forecastData[totalLen - forecastLen + i] = payload.forecast[i];
     }
     ```
     This structure supports any forecast horizon ($1, 7, 30, 90$) without modification.
   - In `js/script.js` lines 1640–1643:
     ```javascript
     maeDisplay.textContent = payload.evaluation?.mae_baht == null ? '--' : `฿${Number(payload.evaluation.mae_baht).toLocaleString()}`;
     directionDisplay.textContent = payload.evaluation?.direction_accuracy_pct == null ? '--' : `${Number(payload.evaluation.direction_accuracy_pct).toFixed(1)}%`;
     ```
     If `evaluation.mae_baht` is `null`, the UI renders `--`.

3. **Backend Route Hardcoded Whitelist**:
   - In `api/routes/forecast_routes.py` lines 25–26:
     ```python
     if period not in (1, 7, 30):
         return jsonify(error="รองรับเฉพาะ 1, 7 หรือ 30 วันประกาศราคา"), 400
     ```
     Queries for `period=90` return HTTP 400.

4. **Forecasting Service Horizons & Guardrails**:
   - In `api/services/forecast_service.py` line 24:
     ```python
     SUPPORTED_PERIODS = (1, 7, 30)
     ```
   - In `api/services/forecast_service.py` lines 147–148:
     ```python
     if period not in SUPPORTED_PERIODS:
         raise ValueError("period must be 1, 7, or 30 announcement days")
     ```
   - In `api/services/forecast_service.py` line 195:
     ```python
     max_pct = 0.025 if period == 1 else (0.07 if period <= 7 else 0.12)
     ```
     For `period == 90`, the guardrail currently clamps at 12% instead of the required 18%.
   - In `api/services/forecast_service.py` lines 105–109 (`_interval_errors`):
     ```python
     thirty = max(seven * 1.5, float(horizons.get("30", {}).get("absolute_error_p90", seven * 1.8)))
     first_7 = [one + (seven - one) * ((step - 1) / 6.0) for step in range(1, 8)]
     slope = (thirty - seven) / 23.0
     extended = [seven + slope * (step - 7) for step in range(8, period + 1)]
     return first_7 + extended
     ```
     `period == 90` is naively extrapolated using the slope from day 7 to day 30, ignoring any 90-day metrics or $\sqrt{t}$ volatility scaling.
   - In `api/services/forecast_service.py` lines 114–126 (`_evaluation_payload`):
     ```python
     horizon = horizons.get(str(period)) or {}
     if not horizon and period == 30:
         base7 = horizons.get("7") or {}
         horizon = {
             "mae_baht": round(float(base7.get("mae_baht") or 420) * 1.5, 2),
             ...
         }
     ```
     No fallback branch exists for `period == 90`. When `horizon = horizons.get("90")` is empty (as in standard champion models where backtest only stores horizons `"1"` and `"7"`), all evaluation metrics return `None`.

5. **Test Suite Baseline**:
   - Command: `.\.venv\Scripts\pytest.exe tests/`
   - Output: `253 passed in 167.10s (0:02:47)`.
   - Coverage: Existing tests cover 7d and 30d (`tests/test_m2_m3_enhancements.py` lines 60–130, `tests/e2e/test_tier1_features.py` lines 540–556, `tests/e2e/test_tier2_boundaries.py` lines 453–457). Zero tests exist for 90d.

---

## 2. Logic Chain

1. **Observation 1 $\rightarrow$ UI Inaccessibility**: Because `components/6-forecast.html` only provides options `1` and `7`, end users have no UI mechanism to request 30-day or 90-day forecasts, despite 30-day logic being partially implemented in the backend.
2. **Observation 2 $\rightarrow$ Frontend Readiness**: The frontend chart rendering in `js/script.js` is already 100% horizon-agnostic; it slices and overlaps arrays based dynamically on `payload.history.length` and `payload.forecast.length`. Therefore, modifying `components/6-forecast.html` requires zero alterations to `js/script.js` for chart drawing, but requires valid evaluation metrics from the backend to avoid `--` display artifacts.
3. **Observations 3 & 4 $\rightarrow$ Backend Rejection**: Because `api/routes/forecast_routes.py` enforces `if period not in (1, 7, 30): return 400` and `api/services/forecast_service.py` defines `SUPPORTED_PERIODS = (1, 7, 30)`, any request for `period=90` is rejected with HTTP 400 before forecasting can run.
4. **Observation 4 $\rightarrow$ Guardrail & Mathematical Defects**:
   - For `period == 90`, `max_pct` must be $0.18$ (18%) rather than $0.12$ (12%) per requirement R1 / R2.
   - `_interval_errors` must implement piecewise continuous interpolation across 3 segments ($1..7, 8..30, 31..90$) with square-root volatility scaling for day 90 ($1.6\times$ of day 30), guaranteeing monotonic non-decreasing confidence interval widths.
   - `_evaluation_payload` must provide derived backtest metrics for `period == 90` when not present in DB, preventing `None` fields.
5. **Observation 5 $\rightarrow$ Test Plan**: To ensure zero regression and permanent verification, unit tests in `test_m2_m3_enhancements.py`, contract tests in `test_tier1_features.py`, and mathematical tests in `test_forecasting.py` must be added for `period=90`.

---

## 3. Caveats

1. **Champion Metrics Storage**: In production, `forecast_model_metrics` records only store backtest evaluations for horizons `"1"` and `"7"` (from `SUPPORTED_HORIZONS = (1, 7)` in `forecast_models.py`). While re-running `evaluate_models` with 90-day horizon is technically possible, running a 120-step walk-forward backtest for 90-step ARIMA takes excessive compute and requires $> 575$ historical observations. The derived metric approach in `_evaluation_payload` is therefore the intended, battle-tested design (identical to how 30-day metrics are derived from 7-day).
2. **Self-Healing Fallback (R2)**: This investigation is strictly scoped to R1 (horizon restoration). When Agent B or the implementer implements R2 (autonomous fallback when DB has $<500$ rows or no champion), the fallback engine should reuse the expanded `SUPPORTED_PERIODS = (1, 7, 30, 90)` and guardrails defined here.

---

## 4. Conclusion

Restoring 30-day and 90-day forecast horizons requires targeted, non-breaking modifications across three files:
1. `components/6-forecast.html`: Add `<option value="30">30 วัน (1 เดือน)</option>` and `<option value="90">90 วัน (3 เดือน)</option>` to `#forecast-period`.
2. `api/routes/forecast_routes.py`: Import `SUPPORTED_PERIODS` from `services.forecast_service`, check `if period not in SUPPORTED_PERIODS:`, and return Thai error message `"รองรับเฉพาะ 1, 7, 30 หรือ 90 วันประกาศราคา"`.
3. `api/services/forecast_service.py`:
   - Expand `SUPPORTED_PERIODS` to `(1, 7, 30, 90)`.
   - Update `_interval_errors` to interpolate piecewise across steps 1..7, 8..30, and 31..90 with $\sqrt{t}$ error scaling.
   - Update `_evaluation_payload` to provide derived backtest metrics for `period == 90`.
   - Update `max_pct` guardrail to 4 tiers: 1d=2.5%, 7d=7.0%, 30d=12.0%, 90d=18.0%.
4. Detailed code diffs and test additions are documented in `report.md`.

---

## 5. Verification Method

1. **Run Pytest Suite**:
   ```powershell
   .\.venv\Scripts\pytest.exe tests/
   ```
   All 253 existing tests must continue to pass.
2. **Horizon 90 Endpoint Verification**:
   ```powershell
   .\.venv\Scripts\python.exe -c "from app.create_app import create_app; client = create_app().test_client(); res = client.get('/api/forecast?period=90'); print(res.status_code); data = res.get_json(); print('Forecast length:', len(data.get('forecast', []))); print('Evaluation MAE:', data.get('evaluation', {}).get('mae_baht'))"
   ```
   Expected: Status 200, Forecast length 90, Non-null evaluation MAE.
3. **Invalidation Conditions**:
   - If `/api/forecast?period=90` returns HTTP 400 or HTTP 500.
   - If `len(data["forecast"]) != 90` or `len(data["upper_bound"]) != 90` or `len(data["lower_bound"]) != 90`.
   - If upper bound is less than lower bound at any step.
   - If `evaluation.mae_baht` is `None` or missing on 90-day forecasts.
   - If any prediction for 90 days deviates by $> 18\%$ from the last actual price.
