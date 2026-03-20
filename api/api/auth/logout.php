<?php
// /api/api/auth/logout.php

// ปิดการแสดง Error เพื่อให้ได้ JSON ที่ถูกต้องเสมอ
error_reporting(0);
ini_set('display_errors', 0);

require_once __DIR__ . '/../../config/database.php';
session_start();

try {
    $database = new Database();
    $conn = $database->getConnection();
    
    // 1. ดึงข้อมูลผู้ใช้จาก Token ที่อยู่ในคุกกี้
    $user = verifySession($conn);
    $token = $_COOKIE['session_token'] ?? null;

    // 2. ถ้าเจอผู้ใช้ ให้บันทึก Log ก่อน
    if ($user && isset($user['id'])) {
        logActivity($conn, $user['id'], 'USER_LOGOUT');
    }

    // 3. ลบ Session ออกจากฐานข้อมูล (ถ้ามี token)
    if ($token) {
        $stmt = $conn->prepare("DELETE FROM sessions WHERE token = ?");
        $stmt->execute([$token]);
    }

    // 4. สั่งให้เบราว์เซอร์ลบคุกกี้ โดยการกำหนดวันหมดอายุในอดีต
    setcookie('session_token', '', [
        'expires' => time() - 3600,
        'path' => '/',
        'secure' => false,
        'httponly' => true,
        'samesite' => 'Lax'
    ]);
    
    // 5. ตอบกลับสำเร็จ
    sendJSON(['success' => true, 'message' => 'ออกจากระบบสำเร็จ']);

} catch (Exception $e) {
    // กรณีเกิดข้อผิดพลาดร้ายแรง (เช่น DB ล่ม)
    sendJSON(['success' => false, 'message' => 'เกิดข้อผิดพลาดในการออกจากระบบ'], 500);
}
