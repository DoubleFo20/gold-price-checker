-- Add actual price columns for forecast verification
ALTER TABLE saved_forecasts
  ADD COLUMN actual_max_price DECIMAL(10,2) NULL DEFAULT NULL AFTER hist_days,
  ADD COLUMN actual_min_price DECIMAL(10,2) NULL DEFAULT NULL AFTER actual_max_price,
  ADD COLUMN verified_at TIMESTAMP NULL DEFAULT NULL AFTER actual_min_price;
