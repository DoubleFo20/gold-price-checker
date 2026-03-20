<?php
/**
 * cron/check_alerts.php
 * 
 * Cron job สำหรับตรวจสอบและส่งการแจ้งเตือนราคาทอง
 * ควรรันทุก 5-10 นาที
 * 
 * ตัวอย่างการตั้งค่า Cron:
 */

require_once __DIR__ . '/../config/database.php';
require_once __DIR__ . '/../config/line_helper.php';

// บันทึกว่า cron เริ่มทำงาน
$started_at = date('Y-m-d H:i:s');
echo "🔄 Starting alert check at $started_at\n";

try {
    $db = new Database();
    $conn = $db->getConnection();
    
    // 1. ดึงราคาทองปัจจุบัน
    $current_prices = getCurrentGoldPrices();
    
    if (!$current_prices) {
        throw new Exception('Cannot fetch current gold prices');
    }
    
    echo "📊 Current prices fetched:\n";
    echo "   Gold bar: ฿" . number_format($current_prices['bar'], 2) . "\n";
    echo "   Ornament: ฿" . number_format($current_prices['ornament'], 2) . "\n";
    echo "   World: $" . number_format($current_prices['world'], 2) . "\n";
    
    // 2. ดึง alerts ที่ active
    $stmt = $conn->prepare("
        SELECT pa.*, u.email, u.name
        FROM price_alerts pa
        INNER JOIN users u ON pa.user_id = u.id
        WHERE pa.triggered = 0
        ORDER BY pa.created_at ASC
    ");
    $stmt->execute();
    $alerts = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    echo "📋 Found " . count($alerts) . " active alerts\n";
    
    $triggered_count = 0;
    
    // 3. ตรวจสอบแต่ละ alert
    foreach ($alerts as $alert) {
        $should_trigger = false;
        $current_price = 0;
        
        // เลือกราคาตาม gold_type
        switch ($alert['gold_type']) {
            case 'bar':
                $current_price = $current_prices['bar'];
                break;
            case 'ornament':
                $current_price = $current_prices['ornament'];
                break;
            case 'world':
                $current_price = $current_prices['world'];
                break;
        }
        
        // ตรวจสอบเงื่อนไข
        if ($alert['alert_type'] === 'above' && $current_price >= $alert['target_price']) {
            $should_trigger = true;
        } elseif ($alert['alert_type'] === 'below' && $current_price <= $alert['target_price']) {
            $should_trigger = true;
        }
        
        // ถ้าถึงเงื่อนไข ให้ส่งแจ้งเตือน
        if ($should_trigger) {
            echo "🔔 Triggering alert #{$alert['id']} for {$alert['email']}\n";
            
            // 1. บันทึก In-App Notification (ทำเสมอ)
            $gold_type_th = ['bar' => 'ทองคำแท่ง', 'ornament' => 'ทองรูปพรรณ', 'world' => 'ทองโลก'];
            $type_text = $gold_type_th[$alert['gold_type']] ?? $alert['gold_type'];
            $alert_type_th = $alert['alert_type'] === 'above' ? 'สูงกว่า' : 'ต่ำกว่า';
            
            $notif_title = "🔔 แจ้งเตือนราคาทอง: {$type_text}";
            $notif_msg = "ราคา{$type_text} ตอนนี้ {$alert_type_th} ฿" . number_format($alert['target_price'], 2) . " แล้ว (ราคาปัจจุบัน: ฿" . number_format($current_price, 2) . ")";
            
            $notif_stmt = $conn->prepare("
                INSERT INTO notifications (user_id, title, message, type, link)
                VALUES (?, ?, ?, 'price_alert', '#price-today-section')
            ");
            $notif_stmt->execute([$alert['user_id'], $notif_title, $notif_msg]);

            // 2. ตรวจสอบช่องทางการส่ง (LINE > Email)
            $user_stmt = $conn->prepare("SELECT line_user_id FROM users WHERE id = ?");
            $user_stmt->execute([$alert['user_id']]);
            $user_data = $user_stmt->fetch(PDO::FETCH_ASSOC);
            
            $line_sent = false;
            if (!empty($user_data['line_user_id'])) {
                echo "   📱 Sending LINE notification...\n";
                $line_msg = "{$notif_title}\n\n{$notif_msg}";
                $line_sent = sendLineNotification($user_data['line_user_id'], $line_msg);
            }

            $email_sent = false;
            if (!$line_sent) {
                echo "   📧 Sending Email notification (as backup)...\n";
                $email_sent = sendAlertEmail($alert, $current_price);
            } else {
                echo "   ✅ LINE sent successfully, skipping Email.\n";
            }

            // อัปเดตสถานะ alert (ถ้าส่งสำเร็จช่องทางใดช่องทางหนึ่ง)
            if ($line_sent || $email_sent) {
                $update_stmt = $conn->prepare("
                    UPDATE price_alerts
                    SET triggered = 1, triggered_at = NOW()
                    WHERE id = ?
                ");
                $update_stmt->execute([$alert['id']]);
                
                // Log activity
                logActivity($conn, $alert['user_id'], 'ALERT_TRIGGERED', json_encode([
                    'alert_id' => $alert['id'],
                    'method' => $line_sent ? 'LINE' : 'EMAIL',
                    'target_price' => $alert['target_price'],
                    'current_price' => $current_price
                ]));
                
                $triggered_count++;
                echo "   ✅ Alert marked as triggered\n";
            } else {
                echo "   ❌ Failed to send notifications\n";
            }
        }
    }
    
    echo "\n📊 Summary:\n";
    echo "   Total alerts checked: " . count($alerts) . "\n";
    echo "   Alerts triggered: $triggered_count\n";
    
    // บันทึกการรัน cron
    $stmt = $conn->prepare("
        INSERT INTO cron_job_runs (job_name, started_at, finished_at, success, details)
        VALUES ('check_alerts', ?, NOW(), 1, ?)
    ");
    $details = json_encode([
        'total_alerts' => count($alerts),
        'triggered' => $triggered_count,
        'prices' => $current_prices
    ]);
    $stmt->execute([$started_at, $details]);
    
    echo "✅ Alert check completed successfully\n";
    
} catch (Exception $e) {
    echo "❌ Error: " . $e->getMessage() . "\n";
    
    // บันทึก error
    if (isset($conn)) {
        $stmt = $conn->prepare("
            INSERT INTO cron_job_runs (job_name, started_at, finished_at, success, details)
            VALUES ('check_alerts', ?, NOW(), 0, ?)
        ");
        $stmt->execute([$started_at, $e->getMessage()]);
    }
    
    exit(1);
}

/**
 * ดึงราคาทองปัจจุบัน
 */
function getCurrentGoldPrices() {
    try {
        // เรียก Python API
        $thai_response = @file_get_contents('http://localhost:5000/api/thai-gold-price');
        $world_response = @file_get_contents('http://localhost:5000/api/world-gold-price');
        
        if (!$thai_response || !$world_response) {
            return null;
        }
        
        $thai_data = json_decode($thai_response, true);
        $world_data = json_decode($world_response, true);
        
        return [
            'bar' => floatval($thai_data['bar_sell'] ?? 0),
            'ornament' => floatval($thai_data['ornament_sell'] ?? 0),
            'world' => floatval($world_data['price_usd_per_ounce'] ?? 0)
        ];
        
    } catch (Exception $e) {
        error_log("Error fetching prices: " . $e->getMessage());
        return null;
    }
}

/**
 * ส่ง email แจ้งเตือน
 */
function sendAlertEmail($alert, $current_price) {
    $to = $alert['email'];
    $name = $alert['name'];
    $target = number_format($alert['target_price'], 2);
    $current = number_format($current_price, 2);
    
    $gold_type_th = [
        'bar' => 'ทองคำแท่ง',
        'ornament' => 'ทองรูปพรรณ',
        'world' => 'ทองโลก (USD/oz)'
    ];
    
    $type_text = $gold_type_th[$alert['gold_type']] ?? $alert['gold_type'];
    
    $alert_type_th = $alert['alert_type'] === 'above' ? 'สูงกว่า' : 'ต่ำกว่า';
    
    $subject = "🔔 แจ้งเตือนราคาทอง - {$type_text}";
    
    $message = "
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            .container { max-width: 600px; margin: 0 auto; padding: 20px; }
            .header { background: linear-gradient(135deg, #d4af37, #c19b2f); color: white; padding: 20px; border-radius: 10px 10px 0 0; }
            .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
            .price { font-size: 32px; font-weight: bold; color: #d4af37; margin: 20px 0; }
            .button { display: inline-block; background: #d4af37; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class='container'>
            <div class='header'>
                <h2>🔔 การแจ้งเตือนราคาทองของคุณถูกเรียกใช้งาน!</h2>
            </div>
            <div class='content'>
                <p>สวัสดี คุณ{$name}</p>
                <p>ราคา<strong>{$type_text}</strong> ตอนนี้ <strong>{$alert_type_th}</strong> ราคาเป้าหมายที่คุณตั้งไว้แล้ว</p>
                
                <p><strong>ราคาปัจจุบัน:</strong></p>
                <div class='price'>฿{$current}</div>
                
                <p><strong>ราคาเป้าหมาย:</strong> ฿{$target}</p>
                
                <p>เข้าชมเว็บไซต์เพื่อดูข้อมูลเพิ่มเติม:</p>
                <a href='http://localhost/gold-price-checker/' class='button'>ดูราคาทองวันนี้</a>
                
                <hr style='margin: 30px 0; border: none; border-top: 1px solid #ddd;'>
                <p style='font-size: 12px; color: #666;'>
                    นี่คือการแจ้งเตือนอัตโนมัติจากระบบ Gold Price Today<br>
                    การแจ้งเตือนนี้จะถูกส่งเพียงครั้งเดียว
                </p>
            </div>
        </div>
    </body>
    </html>
    ";
    
    $headers = "MIME-Version: 1.0\r\n";
    $headers .= "Content-type: text/html; charset=utf-8\r\n";
    $headers .= "From: Gold Price Today <noreply@goldprice.com>\r\n";
    
    // ส่ง email
    return mail($to, $subject, $message, $headers);
}