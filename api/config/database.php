<?php
// D:/xampp/htdocs/gold-price-checker/api/config/database.php

// ===== CORS Headers (ทำงานก่อนเสมอ) =====
if (php_sapi_name() !== 'cli') {
    $origin = $_SERVER['HTTP_ORIGIN'] ?? '';
    $allowed_origins = [
        'http://localhost',
        'http://127.0.0.1',
        'http://localhost:3000',
        'http://localhost:5173',
    ];
    
    // โหลดค่า FRONTEND_ORIGINS จาก config/config.php ถ้ามี
    $config = require __DIR__ . '/config.php';
    if (!empty($config['frontend_origins'])) {
        $extra_origins = explode(',', $config['frontend_origins']);
        foreach ($extra_origins as $o) {
            $allowed_origins[] = trim($o);
        }
    }

    if (in_array($origin, $allowed_origins) || empty($origin)) {
        header("Access-Control-Allow-Origin: " . ($origin ?: '*'));
    } else {
        // ในกรณี Production จริง ควรใส่โดเมนหลักของเว็บที่นี่แทน *
        header("Access-Control-Allow-Origin: " . $origin); 
    }
    
    header("Access-Control-Allow-Credentials: true");
    header("Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS");
    header("Access-Control-Allow-Headers: Content-Type, Authorization, X-Requested-With");

    if ($_SERVER['REQUEST_METHOD'] == 'OPTIONS') {
        http_response_code(204);
        exit;
    }
}
// ===========================================

class Database {
    private $host;
    private $db_name;
    private $username;
    private $password;
    private $charset = "utf8mb4";
    public $conn;

    public function __construct() {
        // โหลดค่า Config จากไฟล์ config.php โดยตรง
        $config = require __DIR__ . '/config.php';

        $this->host = $config['db']['host'] ?? 'localhost';
        $this->db_name = $config['db']['name'] ?? 'goldapidb';
        $this->username = $config['db']['user'] ?? 'root';
        $this->password = $config['db']['pass'] ?? ''; // <-- ปัญหาน่าจะอยู่ตรงนี้
    }

    public function getConnection() {
        $this->conn = null;
        try {
            $dsn = "mysql:host=" . $this->host . ";dbname=" . $this->db_name . ";charset=" . $this->charset;
            $this->conn = new PDO("mysql:host=" . $this->host . ";dbname=" . $this->db_name . ";charset=" . $this->charset, $this->username, $this->password);
            $this->conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

        } catch(PDOException $e) {
            http_response_code(500);
            header('Content-Type: application/json; charset=utf-8');
            echo json_encode(['success' => false, 'message' => 'Database connection failed: ' . $e->getMessage()]);
            exit;
        }
        return $this->conn;
    }
}

// ===== ฟังก์ชัน Helper =====
function sendJSON($data, $status = 200) {
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

function verifySession($conn) {
    $token = $_COOKIE['session_token'] ?? null;
    if (!$token) return null;
    try {
        $stmt = $conn->prepare("SELECT u.* FROM users u INNER JOIN sessions s ON u.id = s.user_id WHERE s.token = ? AND s.expires_at > NOW() LIMIT 1");
        $stmt->execute([$token]);
        return $stmt->fetch();
    } catch(Exception $e) {
        return null;
    }
}

function logActivity($conn, $user_id, $action, $details = null) {
    try {
        $ip = $_SERVER['REMOTE_ADDR'] ?? 'unknown';
        $stmt = $conn->prepare("INSERT INTO activity_logs (user_id, action, ip_address, details) VALUES (?, ?, ?, ?)");
        $stmt->execute([$user_id, $action, $ip, $details]);
    } catch(Exception $e) {
        error_log("Activity log error: " . $e->getMessage());
    }
}