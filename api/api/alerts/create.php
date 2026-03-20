<?php
require_once __DIR__ . '/../../config/database.php';

$database = new Database();
$conn = $database->getConnection();

$me = verifySession($conn);
if (!$me) {
    sendJSON(['success' => false, 'message' => 'ต้องเข้าสู่ระบบ'], 401);
}

$input = json_decode(file_get_contents('php://input'), true) ?? $_POST ?? [];
$target = isset($input['target_price']) ? floatval($input['target_price']) : 0;
$type = trim($input['alert_type'] ?? '');
$gtype = trim($input['gold_type'] ?? 'bar');
$email = trim($input['email'] ?? '') ?: ($me['email'] ?? '');

if ($target <= 0 || !in_array($type, ['above', 'below'], true)) {
    sendJSON(['success' => false, 'message' => 'กรุณากรอกข้อมูลให้ถูกต้อง'], 422);
}
if (!in_array($gtype, ['bar', 'ornament', 'world'], true)) {
    $gtype = 'bar';
}
if ($email && !filter_var($email, FILTER_VALIDATE_EMAIL)) {
    sendJSON(['success' => false, 'message' => 'อีเมลไม่ถูกต้อง'], 422);
}

try {
    $stmt = $conn->prepare("INSERT INTO price_alerts (user_id, target_price, alert_type, gold_type, channel_email, notify_email) VALUES (?, ?, ?, ?, 1, ?)");
    $stmt->execute([$me['id'], $target, $type, $gtype, $email]);
    sendJSON(['success' => true, 'id' => $conn->lastInsertId()]);
} catch (PDOException $e) {
    if ((string)$e->getCode() === '23000') {
        sendJSON(['success' => false, 'message' => 'มีการตั้งค่าแจ้งเตือนนี้แล้ว'], 409);
    }
    sendJSON(['success' => false, 'message' => 'ไม่สามารถบันทึกการแจ้งเตือนได้'], 500);
}
