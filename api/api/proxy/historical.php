<?php
require_once __DIR__ . '/../../config/app.php';
require_once __DIR__ . '/../../includes/rate_limit.php';

rateLimit('proxy_hist', 60, 60);

$symbol = urlencode($_GET['symbol'] ?? 'XAUUSD');
$apiKey = env('ALPHA_VANTAGE_KEY');
$url = "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={$symbol}&apikey={$apiKey}&outputsize=compact";

$ch = curl_init($url);
curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER=>true, CURLOPT_TIMEOUT=>12]);
$resp = curl_exec($ch);
$code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

http_response_code($code ?: 200);
echo $resp ?: json_encode(['status'=>'error','message'=>'fetch failed']);
