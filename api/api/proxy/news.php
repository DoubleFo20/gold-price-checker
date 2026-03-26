<?php
// /api/api/proxy/news.php - (Final Corrected Version)

error_reporting(0);
ini_set('display_errors', 0);

header('Content-Type: application/json; charset=utf-8');

// --- START: CONFIG SECTION ---
$config = require_once __DIR__ . '/../../config/config.php';
$api_key = $config['api_keys']['newsapi'] ?? '';
// --- END: CONFIG SECTION ---


if (empty($api_key)) {
    http_response_code(500);
    echo json_encode(['status' => 'error', 'message' => 'API Key is missing in the PHP script.']);
    exit;
}

$query = urlencode($_GET['q'] ?? 'gold');
$url = "https://newsapi.org/v2/everything?q={$query}&pageSize=10&language=en&sortBy=publishedAt&apiKey={$api_key}";

// [แก้ไข] ลบ '{' ที่เกินมาออก และแก้ไข User-Agent
$options = [
    'http' => [
        'header' => "User-Agent: GoldPriceChecker/1.0\r\n",
        'timeout' => 10,
        'ignore_errors' => true // เพิ่ม option นี้เพื่อให้ file_get_contents ดึงเนื้อหา error มาด้วย
    ]
];
$context = stream_context_create($options);
$response = file_get_contents($url, false, $context);

// ตรวจสอบว่าการเรียก API สำเร็จหรือไม่จาก response header
// $http_response_header เป็น magic variable ของ PHP
if ($response === FALSE || strpos($http_response_header[0], '200 OK') === false) {
    $error_details = 'Could not connect to NewsAPI server.';
    if (isset($http_response_header[0])) {
         $error_details = $http_response_header[0]; 
    }
    
    // พยายามส่ง HTTP status code ที่ถูกต้องกลับไป
    if(preg_match('/HTTP\/\d\.\d\s(\d+)/', $error_details, $matches)) {
        http_response_code(intval($matches[1]));
    } else {
        http_response_code(502); // Bad Gateway
    }

    // พยายาม decode error จาก NewsAPI
    $decoded_error = json_decode($response, true);
    if(json_last_error() === JSON_ERROR_NONE && isset($decoded_error['message'])) {
        echo json_encode(['status' => 'error', 'message' => $decoded_error['message']]);
    } else {
        echo json_encode(['status' => 'error', 'message' => $error_details]);
    }
    exit;
}

// ถ้าสำเร็จ ก็ส่งข้อมูลที่ได้กลับไป
echo $response;