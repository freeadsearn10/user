<?php
require_once __DIR__ . '/../config/config.php';
require_admin();

global $pdo;

$errors = [];

// Handle create / status toggle / delete
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    verify_csrf();
    $action = $_POST['action'] ?? '';

    if ($action === 'create') {
        $username = trim($_POST['username'] ?? '');
        $email = trim($_POST['email'] ?? '');
        $password = $_POST['password'] ?? '';
        $team_name = trim($_POST['team_name'] ?? '');
        $whatsapp = trim($_POST['whatsapp'] ?? '');
        $status = ($_POST['status'] ?? 'active') === 'suspended' ? 'suspended' : 'active';

        if ($username === '') {
            $errors[] = 'Username is required.';
        }
        if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
            $errors[] = 'Valid email is required.';
        }
        if ($password === '' || strlen($password) < 6) {
            $errors[] = 'Password must be at least 6 characters.';
        }

        if (!$errors) {
            $stmt = $pdo->prepare("SELECT id FROM users WHERE username = ? LIMIT 1");
            $stmt->execute([$username]);
            if ($stmt->fetch()) {
                $errors[] = 'Username already exists.';
            } else {
                $hash = password_hash($password, PASSWORD_BCRYPT);
                $apiKey = generate_api_key();

                $stmt = $pdo->prepare("
                    INSERT INTO users (username, email, password_hash, team_name, whatsapp, api_key, role, status)
                    VALUES (:u, :e, :p, :team, :wa, :api, 'user', :status)
                ");
                $stmt->execute([
                    ':u'    => $username,
                    ':e'    => $email,
                    ':p'    => $hash,
                    ':team' => $team_name,
                    ':wa'   => $whatsapp,
                    ':api'  => $apiKey,
                    ':status' => $status,
                ]);
                flash('success', 'User account created.');
                redirect('/admin/users.php');
            }
        }
    } elseif ($action === 'toggle_status') {
        $id = (int)($_POST['id'] ?? 0);
        $stmt = $pdo->prepare("SELECT status FROM users WHERE id = ? AND role = 'user'");
        $stmt->execute([$id]);
        if ($row = $stmt->fetch()) {
            $newStatus = $row['status'] === 'active' ? 'suspended' : 'active';
            $pdo->prepare("UPDATE users SET status = ? WHERE id = ?")->execute([$newStatus, $id]);
            flash('success', 'User status updated.');
        }
        redirect('/admin/users.php');
    } elseif ($action === 'delete') {
        $id = (int)($_POST['id'] ?? 0);
        $pdo->prepare("DELETE FROM users WHERE id = ? AND role = 'user'")->execute([$id]);
        flash('success', 'User deleted.');
        redirect('/admin/users.php');
    }
}

// Fetch users
$stmt = $pdo->query("
    SELECT u.*,
           (SELECT COUNT(*) FROM assigned_numbers an WHERE an.user_id = u.id) AS numbers_count,
           (SELECT COUNT(*) FROM sms_logs sl WHERE sl.user_id = u.id) AS sms_count
    FROM users u
    WHERE u.role = 'user'
    ORDER BY u.created_at DESC
");
$users = $stmt->fetchAll();

$page_title = 'Users';
$active_nav = 'users';
include __DIR__ . '/includes/header.php';
include __DIR__ . '/includes/sidebar.php';
?>
<div class="app-main">
    <div class="topbar">
        <div>
            <div class="topbar-title">Users</div>
            <div class="topbar-subtitle">Manage client accounts, keys and revenue stats.</div>
        </div>
    </div>

    <?php foreach (get_flashes() as $type => $messages): ?>
        <?php foreach ($messages as $msg): ?>
            <div class="alert alert-<?= htmlspecialchars($type) ?>">
                <?= htmlspecialchars($msg) ?>
            </div>
        <?php endforeach; ?>
    <?php endforeach; ?>

    <?php if ($errors): ?>
        <div class="alert alert-danger">
            <?php foreach ($errors as $e): ?>
                <div><?= htmlspecialchars($e) ?></div>
            <?php endforeach; ?>
        </div>
    <?php endif; ?>

    <div class="grid" style="grid-template-columns: minmax(0, 1.7fr) minmax(0, 1.3fr); gap: 18px;">
        <div class="card">
            <div class="card-title-row">
                <div class="card-title">Existing Users</div>
            </div>
            <div class="table-responsive">
                <table class="table-glass">
                    <thead>
                    <tr>
                        <th>User</th>
                        <th>Team</th>
                        <th>Numbers</th>
                        <th>SMS</th>
                        <th>Balance</th>
                        <th>Status</th>
                        <th></th>
                    </tr>
                    </thead>
                    <tbody>
                    <?php if (!$users): ?>
                        <tr>
                            <td colspan="7" class="text-center text-muted py-3">
                                No users yet.
                            </td>
                        </tr>
                    <?php else: ?>
                        <?php foreach ($users as $u): ?>
                            <tr>
                                <td>
                                    <div><?= htmlspecialchars($u['username']) ?></div>
                                    <div style="font-size:11px;color:#9ca3af;">
                                        <?= htmlspecialchars($u['email']) ?>
                                    </div>
                                </td>
                                <td><?= htmlspecialchars($u['team_name'] ?? '') ?></td>
                                <td><?= (int)$u['numbers_count'] ?></td>
                                <td><?= (int)$u['sms_count'] ?></td>
                                <td>$<?= fmt_amount($u['balance']) ?></td>
                                <td>
                                    <?php if ($u['status'] === 'active'): ?>
                                        <span class="badge badge-success">Active</span>
                                    <?php else: ?>
                                        <span class="badge badge-danger">Suspended</span>
                                    <?php endif; ?>
                                </td>
                                <td class="text-end">
                                    <form method="post" style="display:inline-block;">
                                        <input type="hidden" name="csrf_token" value="<?= htmlspecialchars(csrf_token()) ?>">
                                        <input type="hidden" name="id" value="<?= (int)$u['id'] ?>">
                                        <button type="submit" name="action" value="toggle_status"
                                                class="btn btn-outline btn-xs">
                                            <?= $u['status'] === 'active' ? 'Suspend' : 'Activate' ?>
                                        </button>
                                    </form>
                                    <form method="post" style="display:inline-block;"
                                          onsubmit="return confirm('Delete this user?');">
                                        <input type="hidden" name="csrf_token" value="<?= htmlspecialchars(csrf_token()) ?>">
                                        <input type="hidden" name="id" value="<?= (int)$u['id'] ?>">
                                        <button type="submit" name="action" value="delete"
                                                class="btn btn-outline btn-xs">
                                            Delete
                                        </button>
                                    </form>
                                </td>
                            </tr>
                        <?php endforeach; ?>
                    <?php endif; ?>
                    </tbody>
                </table>
            </div>
        </div>

        <div class="card">
            <div class="card-title-row">
                <div class="card-title">Create User</div>
            </div>
            <form method="post">
                <input type="hidden" name="csrf_token" value="<?= htmlspecialchars(csrf_token()) ?>">
                <input type="hidden" name="action" value="create">

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
                    <label class="label">Team Name</label>
                    <input type="text" name="team_name" class="input"
                           value="<?= htmlspecialchars($_POST['team_name'] ?? '') ?>">
                </div>
                <div class="form-group">
                    <label class="label">WhatsApp Number</label>
                    <input type="text" name="whatsapp" class="input"
                           value="<?= htmlspecialchars($_POST['whatsapp'] ?? '') ?>">
                </div>
                <div class="form-group">
                    <label class="label">Status</label>
                    <select name="status" class="select">
                        <option value="active" selected>Active</option>
                        <option value="suspended">Suspended</option>
                    </select>
                </div>
                <div class="d-grid mt-2">
                    <button type="submit" class="btn btn-primary btn-xs">
                        Create User
                    </button>
                </div>
            </form>
            <p class="text-muted mt-2" style="font-size: 12px;">
                An API key will be generated automatically for each new user.
            </p>
        </div>
    </div>
</div>

<?php include __DIR__ . '/includes/footer.php'; ?>