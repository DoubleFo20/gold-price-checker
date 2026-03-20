<?php
// D:/xampp/htdocs/gold-price-checker/api/api/line/webhook.php
require_once __DIR__ . '/../../config/database.php';
require_once __DIR__ . '/../../config/line_helper.php';

$content = file_get_contents('php://input');
$events = json_decode($content, true);

if (!empty($events['events'])) {
    foreach ($events['events'] as $event) {
        if ($event['type'] == 'message' && $event['message']['type'] == 'text') {
            $replyToken = $event['replyToken'];
            $text = trim($event['message']['text']);
            $userId = $event['source']['userId'];

            $db = new Database();
            $conn = $db->getConnection();

            // ตรวจสอบว่าเป็นรหัสเชื่อมต่อหรือไม่ (เช่น "LINK-12345")
            if (preg_match('/^LINK-(\d+)$/i', $text, $matches)) {
                $linkCode = $matches[1];
                
                // ค้นหา user ที่มีรหัสเชื่อมตอนนี้
                $stmt = $conn->prepare("SELECT id, name FROM users WHERE verification_token = ? AND is_active = 1");
                $stmt->execute([$linkCode]);
                $user = $stmt->fetch(PDO::FETCH_ASSOC);

                if ($user) {
                    // อัปเดต line_user_id
                    $update = $conn->prepare("UPDATE users SET line_user_id = ?, verification_token = NULL WHERE id = ?");
                    $update->execute([$userId, $user['id']]);
                    
                    $replyMsg = "✅ เชื่อมต่อสำเร็จ! สวัสดีคุณ " . $user['name'] . "\nต่อไปนี้คุณจะได้รับแจ้งเตือนราคาทองผ่านช่องทางนี้ครับ";
                } else {
                    $replyMsg = "❌ รหัสเชื่อมต่อไม่ถูกต้อง หรือหมดอายุแล้วครับ";
                }
            } else {
                $replyMsg = "ยินดีต้อนรับสู่ระบบแจ้งเตือนราคาทองคำ!\n\nกรุณาระบุรหัสเชื่อมต่อที่ได้จากหน้าเว็บไซต์ (เช่น LINK-12345) เพื่อเริ่มรับการแจ้งเตือนครับ";
            }

            sendLineReply($replyToken, $replyMsg);
        }
    }
}

function sendLineReply($replyToken, $message) {
    $config = require __DIR__ . '/../../config/config.php';
    $channel_token = $config['line']['channel_token'];

    $url = 'https://api.line.me/v2/bot/message/reply';
    $data = [
        'replyToken' => $replyToken,
        'messages' => [['type' => 'text', 'text' => $message]]
    ];

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/json',
        'Authorization: Bearer ' . $channel_token
    ]);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_exec($ch);
    curl_close($ch);
}
