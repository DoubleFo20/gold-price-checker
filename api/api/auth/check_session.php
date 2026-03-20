<?php
// /api/api/auth/check_session.php

error_reporting(0);
ini_set('display_errors', 0);

// [แก้ไข] เพิ่มการเรียกใช้ config และ database
require_once __DIR__ . '/../../config/database.php';
session_start();

$data = json_decode(file_get_contents("php://input"), true);
// (The previous line can be removed, it's not used here)

// [แก้ไข] สร้างการเชื่อมต่อ DB
$database = new Database();
$conn = $database->getConnection();

try {
    // verifySession() จะตรวจสอบ token ในคุกกี้
    $user = verifySession($conn);

    if ($user) {
        // ถ้าเจอผู้ใช้ ให้ส่งข้อมูลกลับไป
        unset($user['password_hash']); 
        sendJSON([
            'success' => true, 
            'authenticated' => true, 
            'user' => $user
        ]);
    } else {
        // ถ้าไม่เจอ หรือ token หมดอายุ
        setcookie('session_token', '', ['expires' => time() - 3600, 'path' => '/']);
        sendJSON(['success' => true, 'authenticated' => false]);
    }
} catch(Exception $e) {
    sendJSON(['success' => false, 'authenticated' => false, 'message' => 'Server error during session check'], 500);
}