<?php
// D:/xampp/htdocs/gold-price-checker/api/api/profile/generate_line_code.php
require_once __DIR__ . '/../../config/database.php';

header('Content-Type: application/json; charset=utf-8');

$db = new Database();
$conn = $db->getConnection();
$user = verifySession($conn);

if (!$user) {
    sendJSON(["success" => false, "message" => "กรุณาเข้าสู่ระบบ"], 401);
}

try {
    // สุ่มเลข 6 หลัก
    $code = str_pad(mt_rand(0, 999999), 6, '0', STR_PAD_LEFT);
    
    // บันทึกลงใน verification_token เพื่อใช้เป็นตัวเชื่อม (Link Code)
    $stmt = $conn->prepare("UPDATE users SET verification_token = ? WHERE id = ?");
    $stmt->execute([$code, $user['id']]);

    sendJSON([
        "success" => true, 
        "code" => $code,
        "message" => "Code generated successfully"
    ]);
} catch (Exception $e) {
    sendJSON(["success" => false, "message" => "Server Error: " . $e->getMessage()], 500);
}
