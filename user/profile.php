<?php
require_once __DIR__ . '/../config/config.php';
require_user();

global $pdo;
$user = current_user();
$userId = (int)$user['id'];

$errors = [];
$success = false;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    verify_csrf();

    $email = trim($_POST['email'] ?? '');
    $whatsapp = trim($_POST['whatsapp'] ?? '');
    $team_name = trim($_POST['team_name'] ?? '');
    $password = $_POST['password'] ?? '';
    $password2 = $_POST['password_confirm'] ?? '';

    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        $errors[] = 'Valid email is required.';
    }

    if ($password !== '' || $password2 !== '') {
        if (strlen($password) < 6) {
            $errors[] = 'Password must be at least 6 characters.';
        }
        if ($password !== $password2) {
            $errors[] = 'Passwords do not match.';
        }
    }

    if (!$errors) {
        $params = [
            ':email'    => $email,
            ':whatsapp' => $whatsapp,
            ':team'     => $team_name,
            ':id'       => $userId,
        ];
        $sql = "UPDATE users SET email = :email, whatsapp = :whatsapp, team_name = :team";

        if ($password !== '') {
            $sql .= ", password_hash = :ph";
            $params[':ph'] = password_hash($password, PASSWORD_BCRYPT);
        }
        $sql .= " WHERE id = :id";

        $stmt = $pdo->prepare($sql);
        $stmt->execute($params);
        $success = true;
        $user['email'] = $email;
        $user['whatsapp'] = $whatsapp;
        $user['team_name'] = $team_name;
    }
}

$page_title = 'Profile';
$active_nav = 'profile';
include __DIR__ . '/includes/header.php';
include __DIR__ . '/includes/sidebar.php';
?>
<div class="app-main">
    <div class="topbar">
        <div>
            <div class="topbar-title">Profile Settings</div>
            <div class="topbar-subtitle">
                Update your contact details and login password.
            </div>
        </div>
    </div>

    <?php if ($success): ?>
        <div class="alert alert-success">
            Profile updated successfully.
        </div>
    <?php endif; ?>

    <?php if ($errors): ?>
        <div class="alert alert-danger">
            <?php foreach ($errors as $e): ?>
                <div><?= htmlspecialchars($e) ?></div>
            <?php endforeach; ?>
        </div>
    <?php endif; ?>

    <div class="card" style="max-width: 640px;">
        <div class="card-title-row">
            <div class="card-title">Account</div>
        </div>
        <form method="post">
            <input type="hidden" name="csrf_token" value="<?= htmlspecialchars(csrf_token()) ?>">

            <div class="form-group">
                <label class="label">Username</label>
                <input type="text" class="input" value="<?= htmlspecialchars($user['username']) ?>" disabled>
            </div>
            <div class="form-group">
                <label class="label">Email</label>
                <input type="email" name="email" class="input"
                       value="<?= htmlspecialchars($user['email']) ?>">
            </div>
            <div class="form-group">
                <label class="label">WhatsApp Number</label>
                <input type="text" name="whatsapp" class="input"
                       value="<?= htmlspecialchars($user['whatsapp'] ?? '') ?>">
            </div>
            <div class="form-group">
                <label class="label">Team Name</label>
                <input type="text" name="team_name" class="input"
                       value="<?= htmlspecialchars($user['team_name'] ?? '') ?>">
            </div>

            <hr class="my-3">

            <div class="card-title-row">
                <div class="card-title">Change Password</div>
            </div>
            <div class="form-group">
                <label class="label">New Password</label>
                <input type="password" name="password" class="input" autocomplete="new-password">
            </div>
            <div class="form-group">
                <label class="label">Confirm New Password</label>
                <input type="password" name="password_confirm" class="input" autocomplete="new-password">
            </div>

            <div class="d-grid mt-3">
                <button type="submit" class="btn btn-primary btn-xs">
                    Save Changes
                </button>
            </div>
        </form>
    </div>
</div>

<?php include __DIR__ . '/includes/footer.php'; ?>