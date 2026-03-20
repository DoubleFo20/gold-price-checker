<?php // D:\xampp\htdocs\gold-price-checker\api\admin\pages\price_alerts.php ?>

<h1 class="h3 mb-2 text-gray-800">ประวัติการแจ้งเตือนราคา</h1>
<p class="mb-4">ตารางแสดงประวัติการแจ้งเตือนราคาที่ถูกส่งไปยังสมาชิก</p>

<div class="card shadow mb-4">
    <div class="card-header py-3">
        <h6 class="m-0 font-weight-bold text-primary">Price Alerts History</h6>
    </div>
    <div class="card-body">
        <div class="table-responsive">
            <table class="table table-bordered" id="dataTable" width="100%" cellspacing="0">
                <thead>
                    <tr>
                        <th>Alert ID</th><th>User Email</th><th>Type</th><th>Target Price</th><th>Status</th><th>Created At</th>
                    </tr>
                </thead>
                <tbody>
                    <?php
                    try {
                        // ดึงข้อมูล Alerts พร้อมกับข้อมูล email ของ user
                        $stmt = $db->query("SELECT pa.id, u.email, pa.gold_type, pa.alert_type, pa.target_price, pa.triggered, pa.created_at FROM price_alerts pa LEFT JOIN users u ON pa.user_id = u.id ORDER BY pa.id DESC LIMIT 100");
                        
                        // [แก้ไข] เปลี่ยนจาก fetch_assoc() เป็น fetch() ของ PDO
                        while ($row = $stmt->fetch(PDO::FETCH_ASSOC)):
                    ?>
                    <tr>
                        <td><?php echo htmlspecialchars($row['id']); ?></td>
                        <td><?php echo htmlspecialchars($row['email'] ?? 'N/A'); ?></td>
                        <td><?php echo htmlspecialchars(ucfirst($row['gold_type']) . ' ' . $row['alert_type']); ?></td>
                        <td><?php echo number_format($row['target_price'], 2); ?></td>
                        <td>
                            <?php if ($row['triggered']): ?>
                                <span class="badge badge-success">Triggered</span>
                            <?php else: ?>
                                <span class="badge badge-warning">Pending</span>
                            <?php endif; ?>
                        </td>
                        <td><?php echo $row['created_at']; ?></td>
                    </tr>
                    <?php 
                        endwhile; 
                    } catch (PDOException $e) {
                        echo '<tr><td colspan="6">Error fetching data: ' . $e->getMessage() . '</td></tr>';
                    }
                    ?>
                </tbody>
            </table>
        </div>
    </div>
</div>