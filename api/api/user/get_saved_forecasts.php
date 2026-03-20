<?php
// D:/xampp/htdocs/gold-price-checker/api/user/get_saved_forecasts.php
require_once __DIR__ . '/../../config/database.php';

header('Content-Type: application/json; charset=utf-8');

$db = new Database();
$conn = $db->getConnection();
$user = verifySession($conn);

if (!$user) {
    sendJSON(["success" => false, "message" => "กรุณาเข้าสู่ระบบ"], 401);
}

try {
    $stmt = $conn->prepare("
        SELECT id, forecast_date, target_date, trend, max_price, min_price, confidence, hist_days,
               actual_max_price, actual_min_price, verified_at, created_at
        FROM saved_forecasts
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 50
    ");
    $stmt->execute([$user['id']]);
    $forecasts = $stmt->fetchAll();

    sendJSON(["success" => true, "data" => $forecasts]);
} catch (Exception $e) {
    sendJSON(["success" => false, "message" => "Server Error: " . $e->getMessage()], 500);
}
?>
