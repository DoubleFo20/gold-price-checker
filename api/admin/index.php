<?php
// gold-price-checker/api/admin/index.php (Final Corrected Version)

// 1. เรียกใช้ไฟล์ Config หลักของเราโดยตรง
require_once __DIR__ . '/../config/database.php';

// 2. เริ่มการเชื่อมต่อฐานข้อมูล
$database = new Database();
$conn = $database->getConnection(); // <-- สร้างตัวแปรชื่อ $conn

// 3. ตรวจสอบ Session และสิทธิ์ Admin
$user = verifySession($conn); // <-- ส่ง $conn เข้าไป

if (!$user || $user['role'] !== 'admin') {
    header('Location: /gold-price-checker/'); 
    exit;
}

// 4. ถ้าผ่าน ให้แสดงผลหน้า Admin Panel
require_once __DIR__ . '/template.php'; // <-- เรียกใช้ template.php