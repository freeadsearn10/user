<?php
require_once __DIR__ . '/../config/config.php';
require_admin();

global $pdo;

$errors = [];

// Handle create / update / delete
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    verify_csrf();
    $action = $_POST['action'] ?? '';

    if ($action === 'create' || $action === 'update') {
        $name = trim($_POST['name'] ?? '');
        $country = trim($_POST['country'] ?? '');
        $range_code = trim($_POST['range_code'] ?? '');
        $otp_rate = (float)($_POST['otp_rate'] ?? 0);
        $status = ($_POST['status'] ?? 'active') === 'inactive' ? 'inactive' : 'active';

        if ($name === '') {
            $errors[] = 'Route name is required.';
        }
        if ($country === '') {
            $errors[] = 'Country is required.';
        }
        if ($range_code === '') {
            $errors[] = 'Range code is required.';
        }

        if (!$errors) {
            if ($action === 'create') {
                $stmt = $pdo->prepare("
                    INSERT INTO routes (name, country, range_code, otp_rate, status)
                    VALUES (:name, :country, :range_code, :otp_rate, :status)
                ");
                $stmt->execute([
                    ':name'       => $name,
                    ':country'    => $country,
                    ':range_code' => $range_code,
                    ':otp_rate'   => $otp_rate,
                    ':status'     => $status,
                ]);
                flash('success', 'Route created successfully.');
            } else {
                $id = (int)($_POST['id'] ?? 0);
                $stmt = $pdo->prepare("
                    UPDATE routes
                    SET name = :name,
                        country = :country,
                        range_code = :range_code,
                        otp_rate = :otp_rate,
                        status = :status
                    WHERE id = :id
                ");
                $stmt->execute([
                    ':name'       => $name,
                    ':country'    => $country,
                    ':range_code' => $range_code,
                    ':otp_rate'   => $otp_rate,
                    ':status'     => $status,
                    ':id'         => $id,
                ]);
                flash('success', 'Route updated successfully.');
            }
            redirect('/admin/routes.php');
        }
    } elseif ($action === 'delete') {
        $id = (int)($_POST['id'] ?? 0);
        $stmt = $pdo->prepare("DELETE FROM routes WHERE id = ?");
        $stmt->execute([$id]);
        flash('success', 'Route deleted.');
        redirect('/admin/routes.php');
    }
}

$editRoute = null;
if (isset($_GET['edit'])) {
    $id = (int)$_GET['edit'];
    $stmt = $pdo->prepare("SELECT * FROM routes WHERE id = ?");
    $stmt->execute([$id]);
    $editRoute = $stmt->fetch();
}

$stmt = $pdo->query("SELECT * FROM routes ORDER BY country, name");
$routes = $stmt->fetchAll();

$page_title = 'Routes / Ranges';
$active_nav = 'routes';
include __DIR__ . '/includes/header.php';
include __DIR__ . '/includes/sidebar.php';
?>
<div class="app-main">
    <div class="topbar">
        <div>
            <div class="topbar-title">Routes / Ranges</div>
            <div class="topbar-subtitle">Configure payout per range and country.</div>
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
                <div class="card-title">Existing Routes</div>
            </div>
            <div class="table-responsive">
                <table class="table-glass">
                    <thead>
                    <tr>
                        <th>Country</th>
                        <th>Name</th>
                        <th>Range</th>
                        <th>OTP Rate</th>
                        <th>Status</th>
                        <th></th>
                    </tr>
                    </thead>
                    <tbody>
                    <?php if (!$routes): ?>
                        <tr>
                            <td colspan="6" class="text-center text-muted py-3">
                                No routes configured yet.
                            </td>
                        </tr>
                    <?php else: ?>
                        <?php foreach ($routes as $route): ?>
                            <tr>
                                <td><?= htmlspecialchars($route['country']) ?></td>
                                <td><?= htmlspecialchars($route['name']) ?></td>
                                <td><?= htmlspecialchars($route['range_code']) ?></td>
                                <td>$<?= fmt_amount($route['otp_rate']) ?></td>
                                <td>
                                    <?php if ($route['status'] === 'active'): ?>
                                        <span class="badge badge-success">Active</span>
                                    <?php else: ?>
                                        <span class="badge badge-danger">Inactive</span>
                                    <?php endif; ?>
                                </td>
                                <td class="text-end">
                                    <a href="?edit=<?= (int)$route['id'] ?>" class="btn btn-outline btn-xs">Edit</a>
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
                <div class="card-title">
                    <?= $editRoute ? 'Edit Route' : 'Add New Route' ?>
                </div>
            </div>
            <form method="post">
                <input type="hidden" name="csrf_token" value="<?= htmlspecialchars(csrf_token()) ?>">
                <input type="hidden" name="action" value="<?= $editRoute ? 'update' : 'create' ?>">
                <?php if ($editRoute): ?>
                    <input type="hidden" name="id" value="<?= (int)$editRoute['id'] ?>">
                <?php endif; ?>

                <div class="form-group">
                    <label class="label">Route Name</label>
                    <input type="text" name="name" class="input" required
                           value="<?= htmlspecialchars($editRoute['name'] ?? '') ?>">
                </div>
                <div class="form-group">
                    <label class="label">Country</label>
                    <input type="text" name="country" class="input" required
                           value="<?= htmlspecialchars($editRoute['country'] ?? '') ?>">
                </div>
                <div class="form-group">
                    <label class="label">Range Code</label>
                    <input type="text" name="range_code" class="input" required
                           placeholder="e.g., 22507584"
                           value="<?= htmlspecialchars($editRoute['range_code'] ?? '') ?>">
                </div>
                <div class="form-group">
                    <label class="label">OTP Rate (per delivered OTP)</label>
                    <input type="number" step="0.0001" name="otp_rate" class="input"
                           value="<?= htmlspecialchars($editRoute['otp_rate'] ?? '0') ?>">
                </div>
                <div class="form-group">
                    <label class="label">Status</label>
                    <select name="status" class="select">
                        <option value="active" <?= ($editRoute['status'] ?? '') === 'inactive' ? '' : 'selected' ?>>Active</option>
                        <option value="inactive" <?= ($editRoute['status'] ?? '') === 'inactive' ? 'selected' : '' ?>>Inactive</option>
                    </select>
                </div>

                <div class="d-flex align-items-center justify-content-between mt-2">
                    <button type="submit" class="btn btn-primary btn-xs">
                        <?= $editRoute ? 'Update Route' : 'Create Route' ?>
                    </button>

                    <?php if ($editRoute): ?>
                        <button type="submit" name="action" value="delete" class="btn btn-outline btn-xs"
                                onclick="return confirm('Delete this route?');">
                            Delete
                        </button>
                    <?php endif; ?>
                </div>
            </form>
        </div>
    </div>
</div>

<?php include __DIR__ . '/includes/footer.php'; ?>