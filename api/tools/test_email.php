<?php
require_once __DIR__ . '/../includes/email.php';
header('Content-Type:text/plain; charset=utf-8');
$ok = sendEmail(getenv('SMTP_USER'), 'Test Email', '<p>ระบบอีเมลพร้อมใช้งาน</p>');
echo $ok ? "✅ Email sent successfully" : "❌ Failed to send email";
