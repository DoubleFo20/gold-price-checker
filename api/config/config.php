<?php
// /api/config/config.php

// Load .env if not already loaded
$envFile = __DIR__ . '/../.env';
if (file_exists($envFile)) {
    $lines = file($envFile, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    foreach ($lines as $line) {
        if (strpos(trim($line), '#') === 0) continue;
        if (strpos($line, '=') === false) continue;
        putenv(trim($line));
    }
}

return [
    'db' => [
        'host' => getenv('DB_HOST') ?: 'localhost',
        'name' => getenv('DB_NAME') ?: 'goldapidb',
        'user' => getenv('DB_USER') ?: 'root',
        'pass' => getenv('DB_PASS') ?: ''
    ],
    'cookie' => [
        'secure' => getenv('COOKIE_SECURE') === 'true'
    ],
    'api_keys' => [
        'newsapi' => getenv('NEWSAPI_KEY') ?: ''
    ],
    'line' => [
        'channel_token' => getenv('LINE_CHANNEL_ACCESS_TOKEN'),
        'channel_secret' => getenv('LINE_CHANNEL_SECRET')
    ],
    'web_push' => [
        'public_key' => getenv('VAPID_PUBLIC_KEY'),
        'private_key' => getenv('VAPID_PRIVATE_KEY'),
        'subject' => getenv('VAPID_SUBJECT')
    ]
];