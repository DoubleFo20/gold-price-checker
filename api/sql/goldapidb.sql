/* =========================================================
   Gold Trading API - Production Schema
   DB: gold_tracker_db
   Charset/Collation: utf8mb4 / utf8mb4_unicode_ci
   ========================================================= */

-- ปลอดภัยไว้ก่อน
SET NAMES utf8mb4;
SET time_zone = '+07:00';
SET FOREIGN_KEY_CHECKS = 0;   -- ปิดชั่วคราวกัน FK error ระหว่างสร้าง

-- DB
CREATE DATABASE IF NOT EXISTS goldapidb
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE goldapidb;

/* =========================================================
   USERS
   ========================================================= */
CREATE TABLE IF NOT EXISTS users (
  id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  email           VARCHAR(255) NOT NULL,
  password_hash   VARCHAR(255) NOT NULL,
  name            VARCHAR(100),
  email_verified  TINYINT(1) NOT NULL DEFAULT 0,
  verification_token VARCHAR(100) NULL,
  role            ENUM('user','admin') NOT NULL DEFAULT 'user',
  last_login      DATETIME NULL,
  is_active       TINYINT(1) NOT NULL DEFAULT 1,

  -- LINE Messaging API
  line_user_id      VARCHAR(100) NULL,
  line_display_name VARCHAR(100) NULL,

  -- Web Push Notification
  push_subscription JSON NULL,

  created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  -- UPDATED: เพิ่ม UNIQUE + INDEX แยก ค้นไวและกันซ้ำ
  CONSTRAINT uq_users_email UNIQUE (email),
  INDEX idx_users_email (email),
  INDEX idx_users_last_login (last_login),
  INDEX idx_users_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/* =========================================================
   SESSIONS
   ========================================================= */
CREATE TABLE IF NOT EXISTS sessions (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id       INT UNSIGNED NOT NULL,
  -- UPDATED: ใช้ CHAR(64) แน่นอนและ BINARY-friendly
  token         CHAR(64) NOT NULL,
  expires_at    DATETIME NOT NULL,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ip_address    VARCHAR(45),
  user_agent    TEXT,

  -- UPDATED: ดัชนีสำคัญ
  UNIQUE KEY uq_sessions_token (token),
  KEY idx_sessions_user_expires (user_id, expires_at),
  KEY idx_sessions_expires (expires_at),

  -- UPDATED: ตั้งชื่อ FK ชัดเจน + ON UPDATE CASCADE
  CONSTRAINT fk_sessions_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/* =========================================================
   PRICE ALERTS
   ========================================================= */
CREATE TABLE IF NOT EXISTS price_alerts (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id       INT UNSIGNED NOT NULL,
  target_price  DECIMAL(10,2) NOT NULL,
  alert_type    ENUM('above','below') NOT NULL,
  gold_type     ENUM('bar','ornament','world') NOT NULL DEFAULT 'bar',
  channel_email TINYINT(1) NOT NULL DEFAULT 0,
  notify_email  VARCHAR(255) NULL,
  triggered     TINYINT(1) NOT NULL DEFAULT 0,
  triggered_at  DATETIME NULL,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  -- UPDATED: ป้องกันซ้ำ (alert ที่ยังไม่ trigger)
  UNIQUE KEY uq_alert_active (user_id, target_price, alert_type, gold_type, triggered),

  KEY idx_alerts_user_created (user_id, created_at),
  KEY idx_alerts_check (triggered, target_price),

  CONSTRAINT fk_alerts_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/* =========================================================
   CALCULATION HISTORY
   ========================================================= */
CREATE TABLE IF NOT EXISTS calculation_history (
  id                 BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id            INT UNSIGNED NOT NULL,
  weight             DECIMAL(10,3) NOT NULL,
  unit               VARCHAR(20)  NOT NULL,
  result_gram        DECIMAL(10,3),
  result_baht        DECIMAL(10,3),
  bar_buy_value      DECIMAL(12,2),
  bar_sell_value     DECIMAL(12,2),
  jewelry_buy_value  DECIMAL(12,2),
  jewelry_sell_value DECIMAL(12,2),
  created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  KEY idx_calc_user_date (user_id, created_at),
  KEY idx_calc_unit (unit),

  CONSTRAINT fk_calc_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/* =========================================================
   RATE LIMITS (rolling window)
   ========================================================= */
CREATE TABLE IF NOT EXISTS rate_limits (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  identifier  VARCHAR(255) NOT NULL,  -- ip หรือ user key
  action      VARCHAR(50)  NOT NULL,
  ts_unix     INT UNSIGNED NOT NULL,  -- epoch seconds

  -- UPDATED: composite index สำหรับ query ช่วงเวลา
  KEY idx_rate_lookup (identifier, action, ts_unix),
  KEY idx_rate_ts (ts_unix)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/* =========================================================
   EMAIL LOGS
   ========================================================= */
CREATE TABLE IF NOT EXISTS email_logs (
  id               BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id          INT UNSIGNED NULL,
  recipient_email  VARCHAR(255) NOT NULL,
  subject          VARCHAR(255),
  status           ENUM('sent','failed') NOT NULL,
  error_message    TEXT NULL,
  sent_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  -- UPDATED: ดัชนีเรียงดูล่าสุดไว
  KEY idx_email_user_date (user_id, sent_at),
  KEY idx_email_status_date (status, sent_at),
  KEY idx_email_recipient (recipient_email),

  CONSTRAINT fk_email_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/* =========================================================
   PRICE CACHE (optional)
   ========================================================= */
CREATE TABLE IF NOT EXISTS price_cache (
  id             BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  date           DATE NOT NULL,
  bar_buy        DECIMAL(10,2),
  bar_sell       DECIMAL(10,2),
  ornament_buy   DECIMAL(10,2),
  ornament_sell  DECIMAL(10,2),
  world_usd      DECIMAL(10,2),
  world_thb      DECIMAL(10,2),
  created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  UNIQUE KEY uq_pricecache_date (date),
  KEY idx_pricecache_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/* =========================================================
   NEW: API REQUEST LOGS (สำหรับ Debug/Monitoring)
   ========================================================= */
CREATE TABLE IF NOT EXISTS api_request_logs (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id       INT UNSIGNED NULL,
  route         VARCHAR(255) NOT NULL,
  method        VARCHAR(10)  NOT NULL,
  status_code   INT UNSIGNED NOT NULL,
  latency_ms    INT UNSIGNED NULL,
  ip_address    VARCHAR(45)  NULL,
  user_agent    VARCHAR(512) NULL,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  KEY idx_api_route_time (route, created_at),
  KEY idx_api_status_time (status_code, created_at),
  KEY idx_api_user_time (user_id, created_at),

  CONSTRAINT fk_api_logs_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/* =========================================================
   NEW: AUTH LOGS (สำเร็จ/ล้มเหลว)
   ========================================================= */
CREATE TABLE IF NOT EXISTS auth_logs (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id     INT UNSIGNED NULL,
  email       VARCHAR(255) NULL,
  event       ENUM('login_success','login_failed','logout') NOT NULL,
  ip_address  VARCHAR(45) NULL,
  user_agent  VARCHAR(512) NULL,
  created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  KEY idx_auth_user_time (user_id, created_at),
  KEY idx_auth_email_time (email, created_at),
  KEY idx_auth_event_time (event, created_at),

  CONSTRAINT fk_auth_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/* =========================================================
   NEW: CRON JOB RUNS (สถานะการทำงาน cron/check_alerts.php)
   ========================================================= */
CREATE TABLE IF NOT EXISTS cron_job_runs (
  id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  job_name     VARCHAR(100) NOT NULL,  -- e.g. 'check_alerts'
  started_at   DATETIME NOT NULL,
  finished_at  DATETIME NULL,
  success      TINYINT(1) NOT NULL DEFAULT 1,
  details      TEXT NULL,

  KEY idx_cron_name_time (job_name, started_at),
  KEY idx_cron_success_time (success, started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/* =========================================================
   DEMO USER (รหัสผ่าน: demo123456)
   ========================================================= */
INSERT INTO users (email, password_hash, name, is_verified)
VALUES ('demo@goldprice.com',
        '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi',
        'Demo User', 1)
ON DUPLICATE KEY UPDATE email = email; -- กันซ้ำเฉยๆ

/* =========================================================
   ACTIVITY LOGS (ใช้โดย logActivity() ใน database.php)
   ========================================================= */
CREATE TABLE IF NOT EXISTS activity_logs (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id     INT UNSIGNED NULL,
  action      VARCHAR(100) NOT NULL,
  ip_address  VARCHAR(45) NULL,
  details     TEXT NULL,
  created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  KEY idx_activity_user_time (user_id, created_at),
  KEY idx_activity_action (action, created_at),

  CONSTRAINT fk_activity_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/* =========================================================
   NOTIFICATIONS (In-App)
   ========================================================= */
CREATE TABLE IF NOT EXISTS notifications (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id     INT UNSIGNED NOT NULL,
  title       VARCHAR(255) NOT NULL,
  message     TEXT NOT NULL,
  type        ENUM('price_alert', 'forecast_result', 'system') NOT NULL DEFAULT 'system',
  is_read     TINYINT(1) NOT NULL DEFAULT 0,
  link        VARCHAR(255) NULL,
  created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  KEY idx_notif_user_unread (user_id, is_read),
  KEY idx_notif_created (created_at),

  CONSTRAINT fk_notif_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;   -- เปิดกลับ

-- Email verifications (สำหรับยืนยันอีเมล)
CREATE TABLE IF NOT EXISTS email_verifications (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL,
  token VARCHAR(255) UNIQUE NOT NULL,
  expires_at DATETIME NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_user_expires (user_id, expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Password reset tokens
CREATE TABLE IF NOT EXISTS password_resets (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL,
  token VARCHAR(255) UNIQUE NOT NULL,
  expires_at DATETIME NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_user_expires (user_id, expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
