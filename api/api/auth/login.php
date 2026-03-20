<?php
// /api/api/auth/login.php

error_reporting(0);
ini_set('display_errors', 0);

require_once __DIR__ . '/../../config/database.php';
session_start();

$data = json_decode(file_get_contents("php://input"), true);
$email = trim($data['email'] ?? '');
$password = $data['password'] ?? '';

if (empty($email) || empty($password)) {
    sendJSON(['success' => false, 'message' => 'กรุณากรอกอีเมลและรหัสผ่าน'], 400);
}

$database = new Database();
$conn = $database->getConnection();

try {
    $stmt = $conn->prepare("SELECT * FROM users WHERE email = ? AND is_active = 1");
    $stmt->execute([$email]);
    $user = $stmt->fetch();

    if ($user && password_verify($password, $user['password_hash'])) {
        $token = bin2hex(random_bytes(32));
        $expires_timestamp = time() + (86400 * 7); // 7 days from now
        $expires_at_db = date('Y-m-d H:i:s', $expires_timestamp);

        $stmt_session = $conn->prepare("INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)");
        $stmt_session->execute([$user['id'], $token, $expires_at_db]);

        $cookie_secure = ($config['cookie']['secure'] ?? false);
        setcookie('session_token', $token, [
            'expires' => $expires_timestamp,
            'path' => '/',
            'secure' => $cookie_secure,
            'httponly' => true,
            'samesite' => 'Lax'
        ]);

        logActivity($conn, $user['id'], 'USER_LOGIN_SUCCESS');
        unset($user['password_hash']);
        sendJSON(['success' => true, 'message' => 'เข้าสู่ระบบสำเร็จ!', 'user' => $user]);

    } else {
        logActivity($conn, 0, 'USER_LOGIN_FAIL', json_encode(['email' => $email]));
        sendJSON(['success' => false, 'message' => 'อีเมลหรือรหัสผ่านไม่ถูกต้อง'], 401);
    }
} catch (Exception $e) {
    sendJSON(['success' => false, 'message' => 'Server error while processing login.'], 500);
}
