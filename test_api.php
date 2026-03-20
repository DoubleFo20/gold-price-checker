<?php
// gold-price-checker/test_api.php

// ตั้งค่า Header ให้ถูกต้อง เพื่อให้ JavaScript อ่านได้
header('Content-Type: application/json; charset=utf-8');

// สร้างข้อมูล JSON ง่ายๆ เพื่อส่งกลับไป
$response = [
    'success' => true,
    'message' => 'Test API is working correctly!'
];

// ส่งข้อมูลกลับไป
echo json_encode($response);