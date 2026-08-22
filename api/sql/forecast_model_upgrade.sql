-- Forecast model upgrade for existing deployments.
-- IMPORTANT: back up the database and obtain owner approval before running.
-- MySQL does not consistently support ADD COLUMN IF NOT EXISTS. Existing-table
-- columns are therefore added idempotently by tools/apply_forecast_upgrade.py,
-- which checks SHOW COLUMNS before issuing each ALTER. The CREATE TABLE
-- statements below are independently idempotent.

CREATE TABLE IF NOT EXISTS forecast_model_metrics (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  model_name VARCHAR(100) NOT NULL,
  model_version VARCHAR(50) NOT NULL,
  selected TINYINT(1) NOT NULL DEFAULT 0,
  trained_through DATE NOT NULL,
  backtest_start DATE NOT NULL,
  backtest_end DATE NOT NULL,
  observations INT UNSIGNED NOT NULL,
  metrics_json JSON NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_forecast_model_run (model_name, model_version, trained_through),
  KEY idx_forecast_model_selected (selected, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS forecast_predictions (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  model_name VARCHAR(100) NOT NULL,
  model_version VARCHAR(50) NOT NULL,
  trained_through DATE NOT NULL,
  horizon_step TINYINT UNSIGNED NOT NULL,
  projected_target_date DATE NOT NULL,
  actual_target_date DATE NULL,
  origin_price DECIMAL(10,2) NOT NULL,
  predicted_price DECIMAL(10,2) NOT NULL,
  lower_bound DECIMAL(10,2) NOT NULL,
  upper_bound DECIMAL(10,2) NOT NULL,
  actual_price DECIMAL(10,2) NULL,
  absolute_error DECIMAL(10,2) NULL,
  direction_correct TINYINT(1) NULL,
  verified_at TIMESTAMP NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_forecast_prediction (model_version, trained_through, horizon_step),
  KEY idx_forecast_prediction_due (verified_at, trained_through, horizon_step)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
