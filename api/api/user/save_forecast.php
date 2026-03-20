<?php
// D:/xampp/htdocs/gold-price-checker/api/user/save_forecast.php
require_once __DIR__ . '/../../config/database.php';

header('Content-Type: application/json; charset=utf-8');

$db = new Database();
$conn = $db->getConnection();
$user = verifySession($conn);

if (!$user) {
    sendJSON(["success" => false, "message" => "กรุณาเข้าสู่ระบบก่อนบันทึก"], 401);
}

$data = json_decode(file_get_contents("php://input"), true);

$target_date = $data['target_date'] ?? null;
$trend = $data['trend'] ?? null;
$max_price = $data['max_price'] ?? null;
$min_price = $data['min_price'] ?? null;
$confidence = $data['confidence'] ?? null;
$hist_days = $data['hist_days'] ?? null;

if (!$target_date || !$trend || !$max_price || !$min_price || !$confidence || !$hist_days) {
    sendJSON(["success" => false, "message" => "ข้อมูลพยากรณ์ไม่ครบถ้วน"], 400);
}

try {
    $today = date('Y-m-d');
    $stmt = $conn->prepare("INSERT INTO saved_forecasts (user_id, forecast_date, target_date, trend, max_price, min_price, confidence, hist_days) VALUES (?, ?, ?, ?, ?, ?, ?, ?)");
    $stmt->execute([
        $user['id'], 
        $today, 
        $target_date, 
        $trend, 
        $max_price, 
        $min_price, 
        $confidence, 
        $hist_days
    ]);

    logActivity($conn, $user['id'], 'save_forecast', "Saved forecast aiming for $target_date");

    $emailPayload = [
        "email" => $user['email'] ?? '',
        "name" => $user['name'] ?? 'ลูกค้า',
        "target_date" => $target_date,
        "trend" => $trend,
        "max_price" => floatval($max_price),
        "min_price" => floatval($min_price),
        "confidence" => floatval($confidence),
        "hist_days" => intval($hist_days)
    ];

    $emailSent = false;
    $ch = curl_init('http://127.0.0.1:5000/api/forecast/send-email');
    if ($ch !== false) {
        curl_setopt_array($ch, [
            CURLOPT_POST => true,
            CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
            CURLOPT_POSTFIELDS => json_encode($emailPayload, JSON_UNESCAPED_UNICODE),
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => 12
        ]);
        $resp = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($resp !== false && $httpCode >= 200 && $httpCode < 300) {
            $parsed = json_decode($resp, true);
            $emailSent = !empty($parsed['success']);
        }
    }

    $message = $emailSent
        ? "บันทึกข้อมูลพยากรณ์เรียบร้อยแล้ว และส่งเข้าอีเมลแล้ว"
        : "บันทึกข้อมูลพยากรณ์เรียบร้อยแล้ว แต่ยังส่งอีเมลไม่สำเร็จ";

    sendJSON(["success" => true, "email_sent" => $emailSent, "message" => $message]);
} catch (Exception $e) {
    sendJSON(["success" => false, "message" => "Server Error: " . $e->getMessage()], 500);
}
?>
