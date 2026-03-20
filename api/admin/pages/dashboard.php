<?php
// gold-price-checker/api/admin/pages/dashboard.php (PDO Version)

// ตรวจสอบให้แน่ใจว่า $db (การเชื่อมต่อ PDO) ถูกส่งมาจาก template.php แล้ว

try {
    // ดึงข้อมูลทั้งหมดที่ต้องใช้ในหน้านี้ด้วยวิธีของ PDO
    $userCountStmt = $db->query("SELECT COUNT(*) as count FROM users");
    $userCount = $userCountStmt->fetchColumn();

    $alertCountStmt = $db->query("SELECT COUNT(*) as count FROM price_alerts WHERE triggered = 0");
    $alertCount = $alertCountStmt->fetchColumn();

    $sessionCountStmt = $db->query("SELECT COUNT(*) as count FROM sessions WHERE expires_at > NOW()");
    $sessionCount = $sessionCountStmt->fetchColumn();

} catch (PDOException $e) {
    // กรณีเกิด Error ให้แสดงค่าเป็น 0 ไปก่อน
    $userCount = 0;
    $alertCount = 0;
    $sessionCount = 0;
    // (ใน Production อาจจะ log error ไว้)
    error_log("Dashboard Error: " . $e->getMessage());
}

?>

<!-- Page Heading -->
<div class="d-sm-flex align-items-center justify-content-between mb-4">
    <h1 class="h3 mb-0 text-gray-800">ภาพรวมระบบ</h1>
</div>

<!-- Content Row -->
<div class="row">

    <!-- Total Users Card -->
    <div class="col-xl-3 col-md-6 mb-4">
        <div class="card border-left-primary shadow h-100 py-2">
            <div class="card-body">
                <div class="row no-gutters align-items-center">
                    <div class="col mr-2">
                        <div class="text-xs font-weight-bold text-primary text-uppercase mb-1">สมาชิกทั้งหมด</div>
                        <div class="h5 mb-0 font-weight-bold text-gray-800"><?php echo htmlspecialchars($userCount); ?></div>
                    </div>
                    <div class="col-auto"><i class="fas fa-users fa-2x text-gray-300"></i></div>
                </div>
            </div>
        </div>
    </div>

    <!-- Active Sessions Card -->
    <div class="col-xl-3 col-md-6 mb-4">
        <div class="card border-left-success shadow h-100 py-2">
            <div class="card-body">
                <div class="row no-gutters align-items-center">
                    <div class="col mr-2">
                        <div class="text-xs font-weight-bold text-success text-uppercase mb-1">ผู้ใช้ออนไลน์</div>
                        <div class="h5 mb-0 font-weight-bold text-gray-800"><?php echo htmlspecialchars($sessionCount); ?></div>
                    </div>
                    <div class="col-auto"><i class="fas fa-plug fa-2x text-gray-300"></i></div>
                </div>
            </div>
        </div>
    </div>

    <!-- Pending Alerts Card -->
    <div class="col-xl-3 col-md-6 mb-4">
        <div class="card border-left-warning shadow h-100 py-2">
            <div class="card-body">
                <div class="row no-gutters align-items-center">
                    <div class="col mr-2">
                        <div class="text-xs font-weight-bold text-warning text-uppercase mb-1">แจ้งเตือนที่รอทำงาน</div>
                        <div class="h5 mb-0 font-weight-bold text-gray-800"><?php echo htmlspecialchars($alertCount); ?></div>
                    </div>
                    <div class="col-auto"><i class="fas fa-bell fa-2x text-gray-300"></i></div>
                </div>
            </div>
        </div>
    </div>
</div>