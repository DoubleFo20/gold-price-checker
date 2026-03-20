<?php
// D:/xampp/htdocs/gold-price-checker/api/api/notifications/list.php
require_once __DIR__ . '/../../config/database.php';

header('Content-Type: application/json; charset=utf-8');

$db = new Database();
$conn = $db->getConnection();
$user = verifySession($conn);

if (!$user) {
    sendJSON(["success" => false, "message" => "กรุณาเข้าสู่ระบบ"], 401);
}

try {
    // ดึง 20 รายการล่าสุด
    $stmt = $conn->prepare("
        SELECT id, title, message, type, is_read, link, created_at
        FROM notifications
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 20
    ");
    $stmt->execute([$user['id']]);
    $notifications = $stmt->fetchAll(PDO::FETCH_ASSOC);

    // นับจำนวนที่ยังไม่ได้อ่าน
    $stmt_unread = $conn->prepare("SELECT COUNT(*) as unread_count FROM notifications WHERE user_id = ? AND is_read = 0");
    $stmt_unread->execute([$user['id']]);
    $unread_data = $stmt_unread->fetch(PDO::FETCH_ASSOC);

    sendJSON([
        "success" => true,
        "data" => $notifications,
        "unread_count" => (int)$unread_data['unread_count']
    ]);
} catch (Exception $e) {
    sendJSON(["success" => false, "message" => "Server Error: " . $e->getMessage()], 500);
}
