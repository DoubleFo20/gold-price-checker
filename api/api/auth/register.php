<?php
// /api/api/auth/register.php

error_reporting(0);
ini_set('display_errors', 0);

// เรียกใช้ไฟล์ database.php เพื่อให้ทุกอย่างทำงานถูกต้อง
require_once __DIR__ . '/../../config/database.php';

$data = json_decode(file_get_contents("php://input"), true);
$email = trim($data['email'] ?? '');
$password = $data['password'] ?? '';
$name = trim($data['name'] ?? '');

if (empty($email) || !filter_var($email, FILTER_VALIDATE_EMAIL) || empty($password) || strlen($password) < 6 || empty($name)) {
    sendJSON(['success' => false, 'message' => 'ข้อมูลไม่ถูกต้อง กรุณากรอกข้อมูลให้ครบถ้วน'], 400);
}

// สร้างการเชื่อมต่อ DB
$database = new Database();
$conn = $database->getConnection();

try {
    $stmt = $conn->prepare("SELECT id FROM users WHERE email = ?");
    $stmt->execute([$email]);
    if ($stmt->fetch()) {
        sendJSON(['success' => false, 'message' => 'อีเมลนี้ถูกใช้งานแล้ว'], 409);
    }
    
    $password_hash = password_hash($password, PASSWORD_BCRYPT);
    
    $stmt_insert = $conn->prepare("INSERT INTO users (email, password_hash, name, role) VALUES (?, ?, ?, 'user')");
    $stmt_insert->execute([$email, $password_hash, $name]);
    $user_id = $conn->lastInsertId();

    logActivity($conn, $user_id, 'USER_REGISTERED', json_encode(["email" => $email]));
    
    sendJSON(['success' => true, 'message' => 'สมัครสมาชิกสำเร็จ! กรุณาเข้าสู่ระบบ'], 201);
    
} catch(Exception $e) {
    sendJSON(['success' => false, 'message' => 'เกิดข้อผิดพลาดในการสมัครสมาชิก'], 500);
}