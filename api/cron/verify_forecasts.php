<?php
/**
 * cron/verify_forecasts.php
 * 
 * Cron job สำหรับตรวจสอบพยากรณ์ที่ถึงวัน target_date แล้ว
 * โดยดึงราคาจริงจาก Python API (แหล่งเดียวกับ Dashboard)
 * แล้วบันทึกลง actual_max_price, actual_min_price
 * 
 * ควรรันทุก 1 ชั่วโมง หรือวันละ 2 ครั้ง (เช้า/เย็น)
 */

require_once __DIR__ . '/../config/database.php';
require_once __DIR__ . '/../config/line_helper.php';
date_default_timezone_set('Asia/Bangkok');

$started_at = date('Y-m-d H:i:s');
echo "🔄 Starting forecast verification at $started_at\n";

try {
    $db = new Database();
    $conn = $db->getConnection();
    
    // 1. ดึง forecasts ที่ target_date <= วันนี้ แต่ยังไม่ verified
    $today = date('Y-m-d');
    $stmt = $conn->prepare("
        SELECT id, user_id, target_date, max_price, min_price, trend
        FROM saved_forecasts
        WHERE target_date <= ?
          AND verified_at IS NULL
        ORDER BY target_date ASC
    ");
    $stmt->execute([$today]);
    $forecasts = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    echo "📋 Found " . count($forecasts) . " unverified forecasts with target_date <= $today\n";
    
    if (count($forecasts) === 0) {
        echo "✅ No forecasts to verify.\n";
        exit(0);
    }
    
    // 2. ดึงราคาทองจริงจาก Python API (Dashboard source)
    $actual_prices = fetchActualPrices();
    
    if (!$actual_prices) {
        throw new Exception('Cannot fetch actual gold prices from dashboard API');
    }
    
    echo "📊 Actual prices fetched:\n";
    echo "   bar_sell (max): ฿" . number_format($actual_prices['bar_sell'], 2) . "\n";
    echo "   bar_buy  (min): ฿" . number_format($actual_prices['bar_buy'], 2) . "\n";
    
    // 3. อัปเดตแต่ละ forecast ที่ยังไม่ verified
    $verified_count = 0;
    $update_stmt = $conn->prepare("
        UPDATE saved_forecasts
        SET actual_max_price = ?,
            actual_min_price = ?,
            verified_at = NOW()
        WHERE id = ?
    ");
    
    foreach ($forecasts as $forecast) {
        try {
            $update_stmt->execute([
                $actual_prices['bar_sell'],  // actual_max_price = ราคาขายออก (สูงสุด)
                $actual_prices['bar_buy'],   // actual_min_price = ราคารับซื้อ (ต่ำสุด)
                $forecast['id']
            ]);
            $verified_count++;
            
            // ตรวจสอบว่าราคาจริงอยู่ในช่วงพยากรณ์หรือไม่
            $in_range = ($actual_prices['bar_sell'] <= $forecast['max_price'] 
                        && $actual_prices['bar_buy'] >= $forecast['min_price']);
            
            // [เพิ่ม] บันทึก In-App Notification
            $status_text = $in_range ? "แม่นยำ ✅" : "ไม่แม่นยำ ❌";
            $notif_title = "📊 ผลพยากรณ์ทองคำ: {$status_text}";
            $target_date_display = date('d/m/Y', strtotime($forecast['target_date']));
            $notif_msg = "ผลพยากรณ์สำหรับวันที่ {$target_date_display} สรุปคือ {$status_text} (ราคาจริง: ฿" . number_format($actual_prices['bar_sell'], 2) . ")";
            
            $notif_stmt = $conn->prepare("
                INSERT INTO notifications (user_id, title, message, type, link)
                VALUES (?, ?, ?, 'forecast_result', '#forecast-section')
            ");
            $notif_stmt->execute([$forecast['user_id'], $notif_title, $notif_msg]);

            // [อัปเดต] จัดลำดับการส่งแจ้งเตือน: LINE เป็นหลัก, Email เป็นสำรอง
            $user_stmt = $conn->prepare("SELECT email, line_user_id FROM users WHERE id = ?");
            $user_stmt->execute([$forecast['user_id']]);
            $user_data = $user_stmt->fetch(PDO::FETCH_ASSOC);
            
            $line_sent = false;
            if (!empty($user_data['line_user_id'])) {
                $line_msg = "{$notif_title}\n\n{$notif_msg}";
                $line_sent = sendLineNotification($user_data['line_user_id'], $line_msg);
            }

            // ถ้าไม่มี LINE หรือส่งไม่สำเร็จ ให้ส่ง Email เป็นสำรอง (ถ้าต้องการเพิ่มฟังก์ชันส่งเมลผลพยากรณ์)
            // if (!$line_sent) {
            //     sendForecastVerificationEmail($user_data['email'], $forecast, $actual_prices, $in_range);
            // }

            // 4. แสดงสถานะใน Console
            $status = $in_range ? '✅ ตรง' : '❌ ผิด';
            
            echo "   Forecast #{$forecast['id']} (target: {$forecast['target_date']}): $status\n";
            echo "     พยากรณ์: ฿" . number_format($forecast['min_price'], 2) . " - ฿" . number_format($forecast['max_price'], 2) . "\n";
            echo "     จริง:    ฿" . number_format($actual_prices['bar_buy'], 2) . " - ฿" . number_format($actual_prices['bar_sell'], 2) . "\n";
            
        } catch (Exception $e) {
            echo "   ❌ Error updating forecast #{$forecast['id']}: " . $e->getMessage() . "\n";
        }
    }
    
    echo "\n📊 Summary:\n";
    echo "   Total forecasts checked: " . count($forecasts) . "\n";
    echo "   Successfully verified: $verified_count\n";
    
    // บันทึกการรัน cron
    $stmt = $conn->prepare("
        INSERT INTO cron_job_runs (job_name, started_at, finished_at, success, details)
        VALUES ('verify_forecasts', ?, NOW(), 1, ?)
    ");
    $details = json_encode([
        'total_forecasts' => count($forecasts),
        'verified' => $verified_count,
        'actual_prices' => $actual_prices
    ], JSON_UNESCAPED_UNICODE);
    $stmt->execute([$started_at, $details]);
    
    echo "✅ Forecast verification completed successfully\n";
    
} catch (Exception $e) {
    echo "❌ Error: " . $e->getMessage() . "\n";
    
    if (isset($conn)) {
        $stmt = $conn->prepare("
            INSERT INTO cron_job_runs (job_name, started_at, finished_at, success, details)
            VALUES ('verify_forecasts', ?, NOW(), 0, ?)
        ");
        $stmt->execute([$started_at, $e->getMessage()]);
    }
    
    exit(1);
}

/**
 * ดึงราคาทองจริงจาก Python API (แหล่งเดียวกับ Dashboard)
 */
function fetchActualPrices() {
    try {
        $response = @file_get_contents('http://localhost:5000/api/thai-gold-price');
        
        if (!$response) {
            echo "⚠️  Python API not responding, trying PHP fallback...\n";
            return fetchActualPricesFromDB();
        }
        
        $data = json_decode($response, true);
        
        if (!$data || (!isset($data['data']['bar_sell']) && !isset($data['bar_sell']))) {
            echo "⚠️  Invalid response from Python API, trying PHP fallback...\n";
            return fetchActualPricesFromDB();
        }
        
        $payload = isset($data['data']) ? $data['data'] : $data;
        
        $cleanFloat = function($val) {
            return floatval(str_replace(',', '', (string)$val));
        };
        
        return [
            'bar_sell' => $cleanFloat($payload['bar_sell'] ?? 0),
            'bar_buy' => $cleanFloat($payload['bar_buy'] ?? 0),
            'ornament_sell' => $cleanFloat($payload['ornament_sell'] ?? 0),
            'ornament_buy' => $cleanFloat($payload['ornament_buy'] ?? 0),
            'source' => $data['source_note'] ?? 'Python API'
        ];
        
    } catch (Exception $e) {
        echo "⚠️  Error fetching from Python API: " . $e->getMessage() . "\n";
        return fetchActualPricesFromDB();
    }
}

/**
 * Fallback: ดึงราคาจาก price_cache ในฐานข้อมูล
 */
function fetchActualPricesFromDB() {
    try {
        global $conn;
        $stmt = $conn->query("
            SELECT bar_buy, bar_sell, ornament_buy, ornament_sell
            FROM price_cache
            ORDER BY date DESC
            LIMIT 1
        ");
        $row = $stmt->fetch(PDO::FETCH_ASSOC);
        
        if ($row && $row['bar_sell']) {
            return [
                'bar_sell' => floatval($row['bar_sell']),
                'bar_buy' => floatval($row['bar_buy']),
                'ornament_sell' => floatval($row['ornament_sell'] ?? 0),
                'ornament_buy' => floatval($row['ornament_buy'] ?? 0),
                'source' => 'price_cache DB'
            ];
        }
        
        return null;
    } catch (Exception $e) {
        return null;
    }
}
?>
