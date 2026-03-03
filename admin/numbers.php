<?php
require_once __DIR__ . '/../config/config.php';
require_admin();

global $pdo;

$errors = [];

// Handle upload / manual add
if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'add_numbers') {
    verify_csrf();

    $country = trim($_POST['country'] ?? '');
    $range_name = trim($_POST['range_name'] ?? '');
    $otp_rate = (float)($_POST['otp_rate'] ?? 0);
    $route_id = (int)($_POST['route_id'] ?? 0) ?: null;

    if ($country === '') {
        $errors[] = 'Country is required.';
    }
    if ($range_name === '') {
        $errors[] = 'Range name is required.';
    }

    $numbers = [];

    // Manual textarea
    $manual = trim($_POST['numbers'] ?? '');
    if ($manual !== '') {
        foreach (preg_split('/\r\n|\r|\n/', $manual) as $line) {
            $line = trim($line);
            if ($line !== '') {
                $numbers[] = $line;
            }
        }
    }

    // File upload (txt or csv, one number per line)
    if (!empty($_FILES['numbers_file']['tmp_name'])) {
        $content = file_get_contents($_FILES['numbers_file']['tmp_name']);
        if ($content !== false) {
            foreach (preg_split('/\r\n|\r|\n/', $content) as $line) {
                $line = trim($line);
                if ($line !== '') {
                    $numbers[] = $line;
                }
            }
        }
    }

    $numbers = array_values(array_unique($numbers));

    if (!$numbers) {
        $errors[] = 'Please provide at least one number (manual or file).';
    }

    if (!$errors) {
        $stmt = $pdo->prepare("
            INSERT INTO available_numbers (number, country, range_name, route_id, otp_rate, status)
            VALUES (:number, :country, :range_name, :route_id, :otp_rate, 'available')
        ");

        foreach ($numbers as $n) {
            $stmt->execute([
                ':number'     => $n,
                ':country'    => $country,
                ':range_name' => $range_name,
                ':route_id'   => $route_id,
                ':otp_rate'   => $otp_rate,
            ]);
        }
        flash('success', 'Numbers added to pool: ' . count($numbers));
        redirect('/admin/numbers.php');
    }
}

// Fetch data
$routes = $pdo->query("SELECT id, name, country, range_code FROM routes ORDER BY country, name")->fetchAll();
$numbersStmt = $pdo->query("
    SELECT av.*, rt.name AS route_name
    FROM available_numbers av
    LEFT JOIN routes rt ON av.route_id = rt.id
    ORDER BY av.created_at DESC
    LIMIT 200
");
$numbers = $numbersStmt->fetchAll();

$page_title = 'Number Pool';
$active_nav = 'numbers';
include __DIR__ . '/includes/header.php';
include __DIR__ . '/includes/sidebar.php';
?>
<div class="app-main">
    <div class="topbar">
        <div>
            <div class="topbar-title">Number Pool</div>
            <div class="topbar-subtitle">Upload premium SMS numbers and prepare them for assignment.</div>
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
                <div class="card-title">Latest Numbers</div>
            </div>
            <div class="table-responsive">
                <table class="table-glass">
                    <thead>
                    <tr>
                        <th>Number</th>
                        <th>Country</th>
                        <th>Range</th>
                        <th>Route</th>
                        <th>Rate</th>
                        <th>Status</th>
                    </tr>
                    </thead>
                    <tbody>
                    <?php if (!$numbers): ?>
                        <tr>
                            <td colspan="6" class="text-center text-muted py-3">
                                No numbers in pool yet.
                            </td>
                        </tr>
                    <?php else: ?>
                        <?php foreach ($numbers as $n): ?>
                            <tr>
                                <td><?= htmlspecialchars($n['number']) ?></td>
                                <td><?= htmlspecialchars($n['country']) ?></td>
                                <td><?= htmlspecialchars($n['range_name']) ?></td>
                                <td><?= htmlspecialchars($n['route_name'] ?? '-') ?></td>
                                <td>$<?= fmt_amount($n['otp_rate']) ?></td>
                                <td>
                                    <?php if ($n['status'] === 'available'): ?>
                                        <span class="badge badge-success">Available</span>
                                    <?php elseif ($n['status'] === 'assigned'): ?>
                                        <span class="badge badge-warning">Assigned</span>
                                    <?php else: ?>
                                        <span class="badge badge-danger">Disabled</span>
                                    <?php endif; ?>
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
                <div class="card-title">Add Numbers to Pool</div>
            </div>
            <form method="post" enctype="multipart/form-data">
                <input type="hidden" name="csrf_token" value="<?= htmlspecialchars(csrf_token()) ?>">
                <input type="hidden" name="action" value="add_numbers">

                <div class="form-group">
                    <label class="label">Country</label>
                    <input type="text" name="country" class="input" required>
                </div>
                <div class="form-group">
                    <label class="label">Range Name</label>
                    <input type="text" name="range_name" class="input" required
                           placeholder="e.g., Ivory Coast - 22507584">
                </div>
                <div class="form-group">
                    <label class="label">Route (optional)</label>
                    <select name="route_id" class="select">
                        <option value="">No route</option>
                        <?php foreach ($routes as $r): ?>
                            <option value="<?= (int)$r['id'] ?>">
                                <?= htmlspecialchars($r['country'] . ' - ' . $r['name'] . ' (' . $r['range_code'] . ')') ?>
                            </option>
                        <?php endforeach; ?>
                    </select>
                </div>
                <div class="form-group">
                    <label class="label">OTP Rate (payout per OTP)</label>
                    <input type="number" step="0.0001" name="otp_rate" class="input" value="0">
                </div>
                <div class="form-group">
                    <label class="label">Manual Numbers (one per line)</label>
                    <textarea name="numbers" class="textarea" placeholder="2250758467XXX"></textarea>
                </div>
                <div class="form-group">
                    <label class="label">Or Upload TXT/CSV (one number per line)</label>
                    <input type="file" name="numbers_file" class="form-control form-control-sm">
                </div>
                <div class="d-grid mt-2">
                    <button type="submit" class="btn btn-primary btn-xs">
                        Add to Pool
                    </button>
                </div>
            </form>
        </div>
    </div>
</div>

<?php include __DIR__ . '/includes/footer.php'; ?>