CREATE TABLE IF NOT EXISTS saved_forecasts (
  id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id         INT UNSIGNED NOT NULL,
  forecast_date   DATE NOT NULL,  -- วันที่ทำการพยากรณ์
  target_date     DATE NOT NULL,  -- วันในอนาคตที่สิ้นสุดการพยากรณ์
  trend           VARCHAR(50) NOT NULL, -- แนวโน้ม
  max_price       DECIMAL(10,2) NOT NULL,
  min_price       DECIMAL(10,2) NOT NULL,
  confidence      DECIMAL(5,2) NOT NULL,
  hist_days       INT NOT NULL,   -- ข้อมูลย้อนหลังเชิงลึกที่ใช้
  created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  KEY idx_forecasts_user_created (user_id, created_at),
  CONSTRAINT fk_forecasts_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
