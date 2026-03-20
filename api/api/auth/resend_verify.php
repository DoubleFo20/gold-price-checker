<?php
require_once '../../config/database.php';
require_once '../../config/app.php';
require_once '../../includes/email.php';

setCorsHeaders();
$user = getCurrentUser();
if (!$user) errorResponse('ต้องเข้าสู่ระบบ', 401);
if ((int)$user['is_verified'] === 1) errorResponse('ยืนยันแล้ว', 400);

$token = bin2hex(random_bytes(32));
$exp = date('Y-m-d H:i:s', time()+1800);
dbQuery("INSERT INTO email_verifications (user_id, token, expires_at) VALUES (?,?,?)",
       [$user['id'], $token, $exp], 'iss');
sendVerificationEmail($user['email'], $token);

successResponse([], 'ส่งอีเมลยืนยันอีกครั้งแล้ว');
