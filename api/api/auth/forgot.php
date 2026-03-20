<?php
require_once '../../config/database.php';
require_once '../../config/app.php';
require_once '../../includes/email.php';
setCorsHeaders();

$input = getJsonInput();
$email = trim($input['email'] ?? '');
if (!$email) errorResponse('กรอกอีเมล', 400);

$user = dbFetchOne("SELECT id,email FROM users WHERE email=?", [$email], 's');
// ตอบสำเร็จเสมอ (ไม่บอกว่าอีเมลมี/ไม่มี)
if ($user) {
  $token = bin2hex(random_bytes(32));
  $exp = date('Y-m-d H:i:s', time()+1800);
  dbQuery("INSERT INTO password_resets (user_id, token, expires_at) VALUES (?,?,?)",
         [$user['id'], $token, $exp], 'iss');
  sendPasswordResetEmail($user['email'], $token);
}
successResponse([], 'หากอีเมลนี้มีอยู่ เราได้ส่งลิงก์ตั้งรหัสผ่านแล้ว');
