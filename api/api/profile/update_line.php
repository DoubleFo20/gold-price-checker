<?php
// D:/xampp/htdocs/gold-price-checker/api/api/profile/update_line.php
require_once __DIR__ . '/../../config/database.php';

header('Content-Type: application/json; charset=utf-8');

$db = new Database();
$conn = $db->getConnection();
$user = verifySession($conn);

if (!$user) {
    sendJSON(["success" => false, "message" => "กรุณาเข้าสู่ระบบ"], 401);
}

$data = json_decode(file_get_contents("php://input"), true);
$line_id = $data['line_user_id'] ?? null;
$display_name = $data['display_name'] ?? null;

try {
    $stmt = $conn->prepare("UPDATE users SET line_user_id = ?, line_display_name = ? WHERE id = ?");
    $stmt->execute([$line_id, $display_name, $user['id']]);

    sendJSON(["success" => true, "message" => "เชื่อมต่อ LINE สำเร็จ"]);
} catch (Exception $e) {
    sendJSON(["success" => false, "message" => "Server Error: " . $e->getMessage()], 500);
}
