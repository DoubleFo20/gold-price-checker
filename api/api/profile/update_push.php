<?php
// D:/xampp/htdocs/gold-price-checker/api/api/profile/update_push.php
require_once __DIR__ . '/../../config/database.php';

header('Content-Type: application/json; charset=utf-8');

$db = new Database();
$conn = $db->getConnection();
$user = verifySession($conn);

if (!$user) {
    sendJSON(["success" => false, "message" => "กรุณาเข้าสู่ระบบ"], 401);
}

$subscription = file_get_contents("php://input");

try {
    $stmt = $conn->prepare("UPDATE users SET push_subscription = ? WHERE id = ?");
    $stmt->execute([$subscription, $user['id']]);

    sendJSON(["success" => true, "message" => "Subscription updated"]);
} catch (Exception $e) {
    sendJSON(["success" => false, "message" => "Server Error: " . $e->getMessage()], 500);
}
