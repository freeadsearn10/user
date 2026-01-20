<?php
require_once __DIR__ . '/../config/config.php';
require_admin();

global $pdo;

$errors = [];

if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'assign') {
    verify_csrf();

    $user_id = (int)($_POST['user_id'] ?? 0);
    $numbers = $_POST['number_ids'] ?? [];

    if ($user_id <= 0) {
        $errors[] = 'Please select a user.';
    }
    if (!$numbers || !is_array($numbers)) {
        $errors[] = 'Please select at least one number to assign.';
    }

    if (!$errors) {
        $stmt = $pdo->prepare("
            INSERT IGNORE INTO assigned_numbers (user_id, number_id, assigned_at)
            VALUES (:user_id, :number_id, NOW())
        ");
        $stmtUpdate = $pdo->prepare("UPDATE available_numbers SET status = 'assigned' WHERE id = :id");

        foreach ($numbers as $nid) {
            $nid = (int)$nid;
            if ($nid <= 0) {
                continue;
            }
            $stmt->execute([
                ':user_id'  => $user_id,
                ':number_id'=> $nid,
            ]);
            $stmtUpdate->execute([':id' => $nid]);
        }

        flash('success', 'Numbers assigned successfully.');
        redirect('/admin/assign_numbers.php');
    }
}

// Fetch users & numbers
$users = $pdo->query("SELECT id, username, team_name FROM users WHERE role = 'user' AND status = 'active' ORDER BY username")->fetchAll();
$availableNumbers = $pdo->query("
    SELECT av.id, av.number, av.country, av.range_name
    FROM available_numbers av
    WHERE av.status = 'available'
    ORDER BY av.country, av.range_name, av.number
    LIMIT 500
")->fetchAll();

$page_title = 'Assign Numbers';
$active_nav = 'assign_numbers';
include __DIR__ . '/includes/header.php';
include __DIR__ . '/includes/sidebar.php';
?>
<div class="app-main">
    <div class="topbar">
        <div>
            <div class="topbar-title">Assign Numbers</div>
            <div class="topbar-subtitle">Allocate premium SMS numbers to users and teams.</div>
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

    <div class="card">
        <div class="card-title-row">
            <div class="card-title">Assign Numbers to User</div>
        </div>
        <form method="post">
            <input type="hidden" name="csrf_token" value="<?= htmlspecialchars(csrf_token()) ?>">
            <input type="hidden" name="action" value="assign">

            <div class="row">
                <div class="col-md-4">
                    <div class="form-group">
                        <label class="label">User</label>
                        <select name="user_id" class="select" required>
                            <option value="">Select user</option>
                            <?php foreach ($users as $u): ?>
                                <option value="<?= (int)$u['id'] ?>">
                                    <?= htmlspecialchars($u['username']) ?>
                                    <?php if (!empty($u['team_name'])): ?>
                                        (<?= htmlspecialchars($u['team_name']) ?>)
                                    <?php endif; ?>
                                </option>
                            <?php endforeach; ?>
                        </select>
                    </div>
                    <p class="text-muted" style="font-size: 12px;">
                        Once assigned, numbers are removed from the available pool for all other users.
                    </p>
                </div>
                <div class="col-md-8">
                    <div class="form-group">
                        <label class="label">Available Numbers (multi-select)</label>
                        <select name="number_ids[]" class="select" multiple size="12">
                            <?php foreach ($availableNumbers as $n): ?>
                                <option value="<?= (int)$n['id'] ?>">
                                    <?= htmlspecialchars($n['country']) ?> ·
                                    <?= htmlspecialchars($n['range_name']) ?> ·
                                    <?= htmlspecialchars($n['number']) ?>
                                </option>
                            <?php endforeach; ?>
                        </select>
                    </div>
                </div>
            </div>

            <div class="d-grid mt-2">
                <button type="submit" class="btn btn-primary btn-xs">
                    Assign Selected Numbers
                </button>
            </div>
        </form>
    </div>
</div>

<?php include __DIR__ . '/includes/footer.php'; ?>