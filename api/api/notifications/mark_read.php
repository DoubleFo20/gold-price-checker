<?php
// D:/xampp/htdocs/gold-price-checker/api/api/notifications/mark_read.php
require_once __DIR__ . '/../../config/database.php';

header('Content-Type: application/json; charset=utf-8');

$db = new Database();
$conn = $db->getConnection();
$user = verifySession($conn);

if (!$user) {
    sendJSON(["success" => false, "message" => "กรุณาเข้าสู่ระบบ"], 401);
}

$data = json_decode(file_get_contents("php://input"), true);
$notif_id = $data['id'] ?? null;

try {
    if ($notif_id === 'all') {
        $stmt = $conn->prepare("UPDATE notifications SET is_read = 1 WHERE user_id = ?");
        $stmt->execute([$user['id']]);
    } else if ($notif_id) {
        $stmt = $conn->prepare("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?");
        $stmt->execute([$notif_id, $user['id']]);
    } else {
        sendJSON(["success" => false, "message" => "Invalid ID"], 400);
    }

    sendJSON(["success" => true, "message" => "Updated successfully"]);
} catch (Exception $e) {
    sendJSON(["success" => true, "message" => "Notification storage unavailable", "degraded" => true], 200);
}
