<?php // D:\xampp\htdocs\gold-price-checker\api\admin\pages\activity_logs.php ?>

<h1 class="h3 mb-2 text-gray-800">ประวัติการใช้งาน</h1>
<p class="mb-4">ตารางแสดงประวัติการกระทำต่างๆ ที่เกิดขึ้นในระบบ</p>

<div class="card shadow mb-4">
    <div class="card-header py-3">
        <h6 class="m-0 font-weight-bold text-primary">Activity Logs</h6>
    </div>
    <div class="card-body">
        <div class="table-responsive">
            <table class="table table-bordered" id="dataTable" width="100%" cellspacing="0">
                <thead>
                    <tr>
                        <th>Log ID</th><th>User (ID / Email)</th><th>Action</th><th>IP Address</th><th>Timestamp</th>
                    </tr>
                </thead>
                <tbody>
                    <?php
                    try {
                        // ดึงข้อมูล Logs พร้อมกับ email ของ user
                        $stmt = $db->query("SELECT al.id, al.user_id, al.action, al.ip_address, al.created_at, u.email FROM activity_logs al LEFT JOIN users u ON al.user_id = u.id ORDER BY al.id DESC LIMIT 200");
                        
                        // [แก้ไข] เปลี่ยนจาก fetch_assoc() เป็น fetch() ของ PDO
                        while ($row = $stmt->fetch(PDO::FETCH_ASSOC)):
                    ?>
                    <tr>
                        <td><?php echo htmlspecialchars($row['id']); ?></td>
                        <td><?php echo htmlspecialchars($row['user_id'] ? $row['user_id'] . ' (' . ($row['email'] ?? 'N/A') . ')' : 'Guest'); ?></td>
                        <td><?php echo htmlspecialchars($row['action']); ?></td>
                        <td><?php echo htmlspecialchars($row['ip_address']); ?></td>
                        <td><?php echo $row['created_at']; ?></td>
                    </tr>
                    <?php 
                        endwhile;
                    } catch (PDOException $e) {
                        echo '<tr><td colspan="5">Error fetching data: ' . $e->getMessage() . '</td></tr>';
                    }
                    ?>
                </tbody>
            </table>
        </div>
    </div>
</div>