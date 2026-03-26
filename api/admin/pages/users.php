<?php // D:\xampp\htdocs\gold-price-checker\api\admin\pages\users.php ?>

<h1 class="h3 mb-2 text-gray-800">จัดการสมาชิก</h1>
<p class="mb-4">ตารางแสดงรายชื่อสมาชิกทั้งหมดในระบบ</p>

<!-- แสดงข้อความแจ้งเตือน -->
<?php if (isset($_GET['delete']) && $_GET['delete'] == 'success'): ?>
    <div class="alert alert-success">ระงับการใช้งานผู้ใช้เรียบร้อยแล้ว</div>
<?php elseif (isset($_GET['update']) && $_GET['update'] == 'success'): ?>
    <div class="alert alert-success">อัปเดตข้อมูลผู้ใช้เรียบร้อยแล้ว</div>
<?php endif; ?>
<?php if (isset($_GET['message'])): ?>
    <div class="alert alert-danger"><?php echo htmlspecialchars($_GET['message']); ?></div>
<?php endif; ?>

<div class="card shadow mb-4">
    <div class="card-header py-3">
        <h6 class="m-0 font-weight-bold text-primary">รายชื่อสมาชิก</h6>
    </div>
    <div class="card-body">
        <div class="table-responsive">
            <table class="table table-bordered" id="dataTable" width="100%" cellspacing="0">
                <thead>
                    <tr>
                        <th>ID</th><th>Name</th><th>Email</th><th>Role</th><th>Verified</th><th>Created At</th><th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <?php
                    try {
                        // ดึงเฉพาะผู้ใช้ที่ยัง active อยู่
                        $stmt = $db->query("SELECT id, name, email, role, is_verified, created_at FROM users WHERE is_active = 1");
                        while ($row = $stmt->fetch(PDO::FETCH_ASSOC)):
                    ?>
                    <tr>
                        <td><?php echo htmlspecialchars($row['id']); ?></td>
                        <td><?php echo htmlspecialchars($row['name']); ?></td>
                        <td><?php echo htmlspecialchars($row['email']); ?></td>
                        <td><?php echo htmlspecialchars($row['role']); ?></td>
                        <td><?php echo $row['is_verified'] ? 'Yes' : 'No'; ?></td>
                        <td><?php echo $row['created_at']; ?></td>
                        <td>
                            <!-- ลิงก์ Edit ชี้ไปที่ index.php ตามปกติ -->
                            <a href="index.php?page=edit_user&id=<?php echo $row['id']; ?>" class="btn btn-warning btn-sm"><i class="fas fa-edit"></i> Edit</a>
                            <!-- ลิงก์ Delete ชี้ไปที่ไฟล์ delete_user.php โดยตรง พร้อม CSRF Token -->
                            <a href="pages/delete_user.php?id=<?php echo $row['id']; ?>&csrf_token=<?php echo $_SESSION['csrf_token']; ?>" class="btn btn-danger btn-sm" onclick="return confirm('คุณแน่ใจหรือไม่ที่จะระงับผู้ใช้นี้?');"><i class="fas fa-trash"></i> Delete</a>
                        </td>
                    </tr>
                    <?php endwhile; } catch (PDOException $e) { 
                        echo '<tr><td colspan="7">Error: ' . $e->getMessage() . '</td></tr>';
                    } ?>
                </tbody>
            </table>
        </div>
    </div>
</div>