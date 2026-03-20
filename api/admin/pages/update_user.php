<?php
// D:\xampp\htdocs\gold-price-checker\api\admin\pages\update_user.php

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

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Location: ../index.php?page=users');
    exit;
}

$user_id = filter_input(INPUT_POST, 'user_id', FILTER_VALIDATE_INT);
$name = trim($_POST['name'] ?? '');
$email = filter_var(trim($_POST['email'] ?? ''), FILTER_SANITIZE_EMAIL);
$role = ($_POST['role'] === 'admin') ? 'admin' : 'user';

$new_pw = $_POST['new_password'] ?? '';
$confirm_pw = $_POST['confirm_password'] ?? '';

if (!$user_id || empty($name) || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
    header("Location: ../index.php?page=edit_user&id={$user_id}&message=" . urlencode("Invalid data."));
    exit;
}

if ($user_id === $user['id'] && $role !== 'admin') {
    header("Location: ../index.php?page=edit_user&id={$user_id}&message=" . urlencode("You cannot change your own role."));
    exit;
}

if (!empty($new_pw)) {
    if (strlen($new_pw) < 6) {
        header("Location: ../index.php?page=edit_user&id={$user_id}&message=" . urlencode("Password must be at least 6 characters."));
        exit;
    }
    if ($new_pw !== $confirm_pw) {
        header("Location: ../index.php?page=edit_user&id={$user_id}&message=" . urlencode("Passwords do not match."));
        exit;
    }
}

try {
    if (!empty($new_pw)) {
        $hash = password_hash($new_pw, PASSWORD_DEFAULT);
        $stmt = $conn->prepare("UPDATE users SET name = ?, email = ?, role = ?, password_hash = ? WHERE id = ?");
        $stmt->execute([$name, $email, $role, $hash, $user_id]);
    } else {
        $stmt = $conn->prepare("UPDATE users SET name = ?, email = ?, role = ? WHERE id = ?");
        $stmt->execute([$name, $email, $role, $user_id]);
    }
    
    logActivity($conn, $user['id'], 'ADMIN_UPDATE_USER', json_encode(['updated_user_id' => $user_id]));

    header("Location: ../index.php?page=users&update=success");
} catch (PDOException $e) {
    header("Location: ../index.php?page=edit_user&id={$user_id}&message=" . urlencode("Database error: " . $e->getMessage()));
}
exit;