<?php
header('Content-Type:text/plain; charset=utf-8');
echo "=== PHP ERROR LOG ===\n";
@readfile(__DIR__ . '/../logs/error.log');
echo "\n\n=== CRON LOG ===\n";
@readfile('/var/log/gold_alerts.log');
