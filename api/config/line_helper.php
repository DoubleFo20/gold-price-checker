<?php
// D:/xampp/htdocs/gold-price-checker/api/config/line_helper.php

function sendLineNotification($line_user_id, $message) {
    $config = require __DIR__ . '/config.php';
    $channel_token = $config['line']['channel_token'];
    
    if (empty($line_user_id) || empty($channel_token)) return false;

    $url = 'https://api.line.me/v2/bot/message/push';
    $data = [
        'to' => $line_user_id,
        'messages' => [
            [
                'type' => 'text',
                'text' => $message
            ]
        ]
    ];

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/json',
        'Authorization: Bearer ' . $channel_token
    ]);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    return ($http_code === 200);
}
