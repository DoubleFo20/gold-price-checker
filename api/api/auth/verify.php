<?php
require_once '../../config/database.php';
require_once '../../config/app.php';

$token = $_GET['token'] ?? '';
if (!$token) errorResponse('โทเค็นไม่ถูกต้อง', 400);

$rec = dbFetchOne("SELECT * FROM email_verifications WHERE token=? AND expires_at > NOW()", [$token], 's');
if (!$rec) errorResponse('โทเค็นหมดอายุหรือไม่ถูกต้อง', 400);

dbQuery("UPDATE users SET is_verified=1 WHERE id=?", [$rec['user_id']], 'i');
dbQuery("DELETE FROM email_verifications WHERE id=?", [$rec['id']], 'i');

// แสดงผลลัพธ์ง่ายๆ หรือ redirect ไปหน้าเว็บ
jsonResponse(['success'=>true,'message'=>'ยืนยันอีเมลสำเร็จ คุณสามารถใช้งานฟีเจอร์ทั้งหมดได้แล้ว']);
    