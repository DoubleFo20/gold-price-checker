<?php
// D:\xampp\htdocs\gold-price-checker\api\admin\pages\edit_user.php

$user_id = filter_input(INPUT_GET, 'id', FILTER_VALIDATE_INT);
if (!$user_id) { 
    header('Location: index.php?page=users&update=error'); 
    exit; 
}

$stmt = $db->prepare("SELECT id, name, email, role FROM users WHERE id = ?");
$stmt->execute([$user_id]);
$user_to_edit = $stmt->fetch();

if (!$user_to_edit) { 
    header('Location: index.php?page=users&update=error'); 
    exit; 
}
?>

<h1 class="h3 mb-4 text-gray-800">แก้ไขข้อมูลผู้ใช้: <?php echo htmlspecialchars($user_to_edit['name']); ?></h1>

<?php if (isset($_GET['message'])): ?>
    <div class="alert alert-danger"><?php echo htmlspecialchars($_GET['message']); ?></div>
<?php endif; ?>

<!-- Action ของฟอร์ม ชี้ไปที่ไฟล์ update_user.php โดยตรง -->
<form action="pages/update_user.php" method="POST">
    <input type="hidden" name="user_id" value="<?php echo htmlspecialchars($user_to_edit['id']); ?>">

    <div class="form-group">
        <label for="name">Name</label>
        <input type="text" class="form-control" id="name" name="name" value="<?php echo htmlspecialchars($user_to_edit['name']); ?>" required>
    </div>
    <div class="form-group">
        <label for="email">Email</label>
        <input type="email" class="form-control" id="email" name="email" value="<?php echo htmlspecialchars($user_to_edit['email']); ?>" required>
    </div>
    <div class="form-group">
        <label for="new_password">New Password (Leave blank to keep current)</label>
        <input type="password" class="form-control" id="new_password" name="new_password" placeholder="Enter new password">
    </div>
    <div class="form-group">
        <label for="confirm_password">Confirm New Password</label>
        <input type="password" class="form-control" id="confirm_password" name="confirm_password" placeholder="Confirm new password">
    </div>

    <div class="form-group">
        <label for="role">Role</label>
        <select class="form-control" id="role" name="role">
            <option value="user" <?php echo ($user_to_edit['role'] === 'user') ? 'selected' : ''; ?>>User</option>
            <option value="admin" <?php echo ($user_to_edit['role'] === 'admin') ? 'selected' : ''; ?>>Admin</option>
        </select>
    </div>

    <button type="submit" class="btn btn-primary">Save Changes</button>
    <a href="index.php?page=users" class="btn btn-secondary">Cancel</a>
</form>