<?php
require_once __DIR__ . '/../config/config.php';

global $pdo;
$stmt = $pdo->query("SELECT COUNT(*) AS c FROM users WHERE role = 'admin'");
$hasAdmin = (int)$stmt->fetchColumn() > 0;

if ($hasAdmin) {
    redirect('/admin/login.php');
}

$errors = [];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    verify_csrf();

    $username = trim($_POST['username'] ?? '');
    $email    = trim($_POST['email'] ?? '');
    $password = $_POST['password'] ?? '';
    $password2 = $_POST['password_confirm'] ?? '';

    if ($username === '') {
        $errors[] = 'Username is required.';
    }
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        $errors[] = 'A valid email address is required.';
    }
    if ($password === '' || strlen($password) < 6) {
        $errors[] = 'Password must be at least 6 characters.';
    }
    if ($password !== $password2) {
        $errors[] = 'Passwords do not match.';
    }

    if (!$errors) {
        // Ensure username uniqueness
        $stmt = $pdo->prepare('SELECT id FROM users WHERE username = ? LIMIT 1');
        $stmt->execute([$username]);
        if ($stmt->fetch()) {
            $errors[] = 'Username is already taken.';
        } else {
            $passwordHash = password_hash($password, PASSWORD_BCRYPT);
            $apiKey = generate_api_key();

            $stmt = $pdo->prepare('INSERT INTO users (username, email, password_hash, api_key, role, status)
                VALUES (:username, :email, :password_hash, :api_key, :role, :status)');
            $stmt->execute([
                ':username'      => $username,
                ':email'         => $email,
                ':password_hash' => $passwordHash,
                ':api_key'       => $apiKey,
                ':role'          => 'admin',
                ':status'        => 'active',
            ]);

            $_SESSION['user_id'] = (int)$pdo->lastInsertId();
            $_SESSION['role'] = 'admin';

            redirect('/admin/dashboard.php');
        }
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Admin Setup | IPRN SMS Panel</title>
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
                    <h5 class="mb-1 text-white">Create Admin Account</h5>
                    <p class="mb-0 text-muted" style="font-size: 13px;">
                        This step will create the first administrator of the panel.
                    </p>
                </div>
                <span class="badge-pill">IPRN SMS Panel</span>
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
                <label class="label">Username</label>
                <input type="text" name="username" class="input" required
                       value="<?= htmlspecialchars($_POST['username'] ?? '') ?>">
            </div>
            <div class="form-group">
                <label class="label">Email</label>
                <input type="email" name="email" class="input" required
                       value="<?= htmlspecialchars($_POST['email'] ?? '') ?>">
            </div>
            <div class="form-group">
                <label class="label">Password</label>
                <input type="password" name="password" class="input" required>
            </div>
            <div class="form-group">
                <label class="label">Confirm Password</label>
                <input type="password" name="password_confirm" class="input" required>
            </div>
            <div class="d-grid mt-3">
                <button type="submit" class="btn btn-primary">
                    Create Admin
                </button>
            </div>
        </form>
    </div>
</div>
</body>
</html>