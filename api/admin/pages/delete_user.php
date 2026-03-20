<?php
// D:\xampp\htdocs\gold-price-checker\api\admin\pages\delete_user.php

// ส่วนหัวสำหรับทำงานด้วยตัวเอง (เชื่อมต่อ DB และตรวจสอบสิทธิ์)
require_once __DIR__ . '/../../config/database.php';
session_start();
$database = new Database($config['db']);
$conn = $database->getConnection();
$user = verifySession($conn); 
if (!$user || $user['role'] !== 'admin') {
    header('Location: ../index.php?page=users&message=' . urlencode('Permission denied.'));
    exit;
}

$user_id_to_delete = filter_input(INPUT_GET, 'id', FILTER_VALIDATE_INT);

if (!$user_id_to_delete) {
    header('Location: ../index.php?page=users&message=' . urlencode('Invalid User ID.'));
    exit;
}

if ($user_id_to_delete === 1) {
    header('Location: ../index.php?page=users&message=' . urlencode('Cannot deactivate the main administrator.'));
    exit;
}

if ($user_id_to_delete === $user['id']) {
    header('Location: ../index.php?page=users&message=' . urlencode('You cannot deactivate yourself.'));
    exit;
}

try {
    // ใช้ Soft Delete (ตั้ง is_active = 0)
    $stmt = $conn->prepare("UPDATE users SET is_active = 0 WHERE id = ?");
    $stmt->execute([$user_id_to_delete]);

    if ($stmt->rowCount() > 0) {
        logActivity($conn, $user['id'], 'ADMIN_DEACTIVATE_USER', json_encode(['deactivated_user_id' => $user_id_to_delete]));
        header('Location: ../index.php?page=users&delete=success');
    } else {
        header('Location: ../index.php?page=users&message=' . urlencode('Failed to deactivate user or user not found.'));
    }
} catch (PDOException $e) {
    header('Location: ../index.php?page=users&message=' . urlencode('Database error.'));
}
exit;