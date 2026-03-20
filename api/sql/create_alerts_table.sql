CREATE TABLE IF NOT EXISTS price_alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    target_price DECIMAL(10, 2) NOT NULL,
    gold_type ENUM('bar', 'ornament', 'world') DEFAULT 'bar',
    alert_type ENUM('above', 'below') NOT NULL,
    email VARCHAR(255) NOT NULL,
    triggered TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    triggered_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
