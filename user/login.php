<?php
require_once __DIR__ . '/../config/config.php';

$errors = [];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    verify_csrf();

    $username = trim($_POST['username'] ?? '');
    $password = $_POST['password'] ?? '';

    if ($username === '' || $password === '') {
        $errors[] = 'Username and password are required.';
    } else {
        global $pdo;
        $stmt = $pdo->prepare("SELECT * FROM users WHERE (username = :u OR email = :u) AND role = 'user' LIMIT 1");
        $stmt->execute([':u' => $username]);
        $user = $stmt->fetch();

        if (!$user || !password_verify($password, $user['password_hash'])) {
            $errors[] = 'Invalid username or password.';
        } elseif ($user['status'] !== 'active') {
            $errors[] = 'Your account is suspended. Please contact support.';
        } else {
            $_SESSION['user_id'] = (int)$user['id'];
            $_SESSION['role'] = 'user';
            $pdo->prepare("UPDATE users SET last_login = NOW() WHERE id = ?")->execute([$user['id']]);
            redirect('/user/dashboard.php');
        }
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>User Login | IPRN SMS Panel</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link
        href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
        rel="stylesheet"
        crossorigin="anonymous"
    >
    <link rel="stylesheet" href="/assets/css/style.css">
</head>
<body>
<div class="auth-wrapper">
    <div class="auth-card">
        <div class="mb-3">
            <div class="d-flex align-items-center justify-content-between">
                <div>
                    <h5 class="mb-1 text-white">User Login</h5>
                    <p class="mb-0 text-muted" style="font-size: 13px;">
                        Access your numbers, live OTPs and revenue in real-time.
                    </p>
                </div>
                <span class="badge-pill">User Panel</span>
            </div>
        </div>

        <?php if ($errors): ?>
            <div class="alert alert-danger">
                <?php foreach ($errors as $e): ?>
                    <div><?= htmlspecialchars($e) ?></div>
                <?php endforeach; ?>
            </div>
        <?php endif; ?>

        <form method="post" autocomplete="off">
            <input type="hidden" name="csrf_token" value="<?= htmlspecialchars(csrf_token()) ?>">
            <div class="form-group">
                <label class="label">Username or Email</label>
                <input type="text" name="username" class="input" required
                       value="<?= htmlspecialchars($_POST['username'] ?? '') ?>">
            </div>
            <div class="form-group">
                <label class="label">Password</label>
                <input type="password" name="password" class="input" required>
            </div>
            <div class="d-grid mt-3">
                <button type="submit" class="btn btn-primary">
                    Sign in
                </button>
            </div>
        </form>
    </div>
</div>
</body>
</html>