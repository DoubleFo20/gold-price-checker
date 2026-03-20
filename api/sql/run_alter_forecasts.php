<?php
/**
 * Run this script once to add actual price columns to saved_forecasts table
 * Usage: php d:/xampp/htdocs/gold-price-checker/api/sql/run_alter_forecasts.php
 */
require_once __DIR__ . '/../config/database.php';

$db = new Database();
$conn = $db->getConnection();

try {
    // Check if columns already exist
    $stmt = $conn->query("SHOW COLUMNS FROM saved_forecasts LIKE 'actual_max_price'");
    if ($stmt->rowCount() > 0) {
        echo "Columns already exist. No changes needed.\n";
        exit(0);
    }

    $conn->exec("
        ALTER TABLE saved_forecasts
          ADD COLUMN actual_max_price DECIMAL(10,2) NULL DEFAULT NULL AFTER hist_days,
          ADD COLUMN actual_min_price DECIMAL(10,2) NULL DEFAULT NULL AFTER actual_max_price,
          ADD COLUMN verified_at TIMESTAMP NULL DEFAULT NULL AFTER actual_min_price
    ");

    echo "✅ Successfully added columns: actual_max_price, actual_min_price, verified_at\n";
} catch (Exception $e) {
    echo "❌ Error: " . $e->getMessage() . "\n";
    exit(1);
}
