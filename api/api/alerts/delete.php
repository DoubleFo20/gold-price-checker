<?php
require_once __DIR__ . '/../../config/database.php';

$database = new Database();
$conn = $database->getConnection();

$me = verifySession($conn);
if (!$me) {
    sendJSON(['success' => false, 'message' => 'ต้องเข้าสู่ระบบ'], 401);
}

$input = json_decode(file_get_contents('php://input'), true) ?? $_POST;
$id = (int)($input['id'] ?? 0);

$stmt = $conn->prepare("DELETE FROM price_alerts WHERE id=? AND user_id=?");
$stmt->execute([$id, $me['id']]);

sendJSON(['success' => true, 'deleted' => $stmt->rowCount() > 0]);
