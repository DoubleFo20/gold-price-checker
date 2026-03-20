<?php
require_once '../../config/database.php';

$database = new Database();
$conn = $database->getConnection();

$me = verifySession($conn);
if (!$me) {
    sendJSON(['success' => false, 'message' => 'ต้องเข้าสู่ระบบ'], 401);
}

$input = json_decode(file_get_contents('php://input'), true) ?? [];
$name = trim($input['name'] ?? '');
if ($name === '' || mb_strlen($name) < 2) {
    sendJSON(['success' => false, 'message' => 'ชื่อไม่ถูกต้อง'], 400);
}

$stmt = $conn->prepare("UPDATE users SET name=? WHERE id=?");
$stmt->execute([$name, $me['id']]);
sendJSON(['success' => true, 'message' => 'อัปเดตโปรไฟล์สำเร็จ']);
