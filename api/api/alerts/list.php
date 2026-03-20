<?php
require_once __DIR__ . '/../../config/database.php';

$database = new Database();
$conn = $database->getConnection();

$me = verifySession($conn);
if (!$me) {
    sendJSON(['success' => false, 'message' => 'ต้องเข้าสู่ระบบ'], 401);
}

$stmt = $conn->prepare("SELECT * FROM price_alerts WHERE user_id=? ORDER BY created_at DESC");
$stmt->execute([$me['id']]);
$res = $stmt->fetchAll(PDO::FETCH_ASSOC);

sendJSON(['success' => true, 'items' => $res]);
