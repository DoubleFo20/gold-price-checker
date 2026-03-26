<?php
// D:/xampp/htdocs/gold-price-checker/api/config/app.php

require_once __DIR__ . '/database.php';

/**
 * ตั้งค่า CORS Headers (ตอนนี้ย้ายไปทำใน database.php แล้ว แต่รักษา function นี้ไว้เพื่อความเข้ากันได้)
 */
function setCorsHeaders() {
    // โค้ด CORS หลักอยู่ใน database.php แล้ว ซึ่งจะทำงานทุกครั้งที่ require database.php
}

/**
 * ส่ง JSON Response สำเร็จ
 */
function successResponse($data = [], $status = 200) {
    $response = array_merge(['success' => true], $data);
    sendJSON($response, $status);
}

/**
 * ส่ง JSON Response ผิดพลาด
 */
function errorResponse($message, $status = 400) {
    sendJSON(['success' => false, 'message' => $message], $status);
}

/**
 * ดึงข้อมูลผู้ใช้ปัจจุบันจาก Session
 */
function getCurrentUser() {
    static $currentUser = null;
    if ($currentUser !== null) return $currentUser;

    $database = new Database();
    $conn = $database->getConnection();
    $currentUser = verifySession($conn);
    return $currentUser;
}

/**
 * ตรวจสอบสิทธิ์ Admin
 */
function requireAdmin() {
    $user = getCurrentUser();
    if (!$user || $user['role'] !== 'admin') {
        errorResponse('Access denied. Admin only.', 403);
    }
    return $user;
}

/**
 * ฟังก์ชันช่วยสร้าง DB Connection แบบรวดเร็ว
 */
function getDBConnection() {
    $database = new Database();
    return $database->getConnection();
}
