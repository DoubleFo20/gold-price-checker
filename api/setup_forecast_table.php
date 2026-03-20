<?php
require_once __DIR__ . '/config/database.php';
$db = new Database();
$conn = $db->getConnection();
$sql = file_get_contents(__DIR__ . '/sql/create_saved_forecasts.sql');
try {
    $conn->exec($sql);
    echo "Table created successfully.";
} catch (PDOException $e) {
    echo "Error: " . $e->getMessage();
}
?>
