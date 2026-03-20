<?php
require_once __DIR__ . '/../config/database.php';
require_once __DIR__ . '/../config/app.php';

header('Content-Type: application/json; charset=utf-8');

$checks = [
    'php_version'   => PHP_VERSION,
    'env_file'      => file_exists(__DIR__ . '/../.env') ? 'ok' : 'missing',
    'database'      => 'pending',
    'python_api'    => 'pending',
    'news_proxy'    => 'pending'
];

try {
    $db = getDBConnection();
    $res = $db->query("SELECT 1");
    $checks['database'] = $res ? 'ok' : 'fail';
} catch (Throwable $e) {
    $checks['database'] = 'fail: ' . $e->getMessage();
}

// Check Python API
$py = @file_get_contents('http://127.0.0.1:5000/api/thai-gold-price');
$checks['python_api'] = $py ? 'ok' : 'fail';

// Check News Proxy
$np = @file_get_contents('http://localhost/api/proxy/news.php?q=gold');
$checks['news_proxy'] = $np ? 'ok' : 'fail';

echo json_encode([
    'status' => 'ok',
    'service' => 'Gold Trading API Health Check',
    'checks' => $checks
], JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
