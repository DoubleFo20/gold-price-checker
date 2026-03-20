<?php
require_once __DIR__ . '/../config/database.php';
header('Content-Type:text/plain; charset=utf-8');

$keys = [
 'DB_HOST','DB_NAME','DB_USER','DB_PASS','NEWSAPI_KEY',
 'ALPHA_VANTAGE_KEY','SMTP_HOST','SMTP_PORT','SMTP_USER','SMTP_PASS',
 'SMTP_FROM_EMAIL','SMTP_FROM_NAME','APP_ENV','APP_URL'
];

foreach ($keys as $k) {
  printf("%-20s : %s\n", $k, getenv($k) ?: '(not set)');
}

$envPath = __DIR__.'/../.env';
clearstatcache();
echo "\n.env permissions : ";
echo file_exists($envPath) ? substr(sprintf('%o', fileperms($envPath)), -3) : 'missing';
echo "\n";
