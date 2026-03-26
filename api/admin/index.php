<?php
// gold-price-checker/api/admin/index.php (Final Corrected Version)

// 1. เรียกใช้ไฟล์ Config หลักของเราโดยตรง
require_once __DIR__ . '/../config/database.php';
session_start();

// 2. เริ่มการเชื่อมต่อฐานข้อมูล
$database = new Database();
$conn = $database->getConnection();

// 3. ตรวจสอบ Session และสิทธิ์ Admin
$user = verifySession($conn);

if (!$user || $user['role'] !== 'admin') {
    header('Location: /gold-price-checker/'); 
    exit;
}

// 3.1. สร้าง CSRF Token ถ้ายังไม่มี
if (empty($_SESSION['csrf_token'])) {
    $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
}

// 4. ถ้าผ่าน ให้แสดงผลหน้า Admin Panel
require_once __DIR__ . '/template.php'; // <-- เรียกใช้ template.php