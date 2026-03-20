<?php
require_once '../../config/database.php';
require_once '../../config/app.php';
setCorsHeaders();

$input = getJsonInput();
$token = $input['token'] ?? '';
$new  = $input['password'] ?? '';

if (!$token || strlen($new) < 6) errorResponse('ข้อมูลไม่ถูกต้อง', 400);

$rec = dbFetchOne("SELECT * FROM password_resets WHERE token=? AND expires_at > NOW()", [$token], 's');
if (!$rec) errorResponse('โทเค็นหมดอายุ/ไม่ถูกต้อง', 400);

$hash = password_hash($new, PASSWORD_DEFAULT);
dbQuery("UPDATE users SET password_hash=? WHERE id=?", [$hash, $rec['user_id']], 'si');
dbQuery("DELETE FROM password_resets WHERE user_id=?", [$rec['user_id']], 'i');

successResponse([], 'ตั้งรหัสผ่านใหม่สำเร็จ');
