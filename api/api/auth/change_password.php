<?php
require_once '../../config/database.php';

$database = new Database();
$conn = $database->getConnection();

$me = verifySession($conn);
if (!$me) {
    sendJSON(['success' => false, 'message' => 'ต้องเข้าสู่ระบบ'], 401);
}

$input = json_decode(file_get_contents('php://input'), true) ?? [];
$old = $input['old_password'] ?? '';
$new = $input['new_password'] ?? '';
if (!$old || mb_strlen($new) < 6) {
    sendJSON(['success' => false, 'message' => 'ข้อมูลไม่ถูกต้อง'], 400);
}

$stmt = $conn->prepare("SELECT password_hash FROM users WHERE id=?");
$stmt->execute([$me['id']]);
$user = $stmt->fetch();
if (!$user || !password_verify($old, $user['password_hash'])) {
    sendJSON(['success' => false, 'message' => 'รหัสผ่านเดิมไม่ถูกต้อง'], 400);
}

$hash = password_hash($new, PASSWORD_DEFAULT);
$stmt = $conn->prepare("UPDATE users SET password_hash=? WHERE id=?");
$stmt->execute([$hash, $me['id']]);
sendJSON(['success' => true, 'message' => 'เปลี่ยนรหัสผ่านสำเร็จ']);
