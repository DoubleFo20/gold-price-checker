<?php
require_once '../../config/database.php';
require_once '../../config/app.php';
setCorsHeaders();

$user = getCurrentUser();
if (!$user) errorResponse('ต้องเข้าสู่ระบบ', 401);

unset($user['password_hash']);
successResponse(['user'=>$user]);
