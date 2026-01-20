<?php
require_once __DIR__ . '/../config/config.php';
require_admin();

global $pdo;

// Toggle status
if (isset($_GET['toggle'])) {
    $id = (int)$_GET['toggle'];
    $stmt = $pdo->prepare("SELECT status FROM api_sources WHERE id = ?");
    $stmt->execute([$id]);
    if ($row = $stmt->fetch()) {
        $newStatus = $row['status'] === 'on' ? 'off' : 'on';
        $pdo->prepare("UPDATE api_sources SET status = ? WHERE id = ?")->execute([$newStatus, $id]);
    }
    redirect('/admin/api_sources.php');
}

// Handle new API source
$errors = [];

if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'create') {
    verify_csrf();

    $name = trim($_POST['name'] ?? '');
    $url = trim($_POST['url'] ?? '');
    $interval = (int)($_POST['poll_interval'] ?? 60);
    $status = ($_POST['status'] ?? 'off') === 'on' ? 'on' : 'off';

    if ($name === '') {
        $errors[] = 'API name is required.';
    }
    if (!filter_var($url, FILTER_VALIDATE_URL)) {
        $errors[] = 'A valid API URL is required.';
    }
    if ($interval < 10) {
        $errors[] = 'Poll interval must be at least 10 seconds.';
    }

    if (!$errors) {
        $stmt = $pdo->prepare("INSERT INTO api_sources (name, url, poll_interval, status)
                               VALUES (:name, :url, :interval, :status)");
        $stmt->execute([
            ':name'     => $name,
            ':url'      => $url,
            ':interval' => $interval,
            ':status'   => $status,
        ]);
        flash('success', 'API source created successfully.');
        redirect('/admin/api_sources.php');
    }
}

// Fetch all sources
$stmt = $pdo->query("SELECT * FROM api_sources ORDER BY created_at DESC");
$sources = $stmt->fetchAll();

$page_title = 'API Sources';
$active_nav = 'api_sources';
include __DIR__ . '/includes/header.php';
include __DIR__ . '/includes/sidebar.php';
?>
<div class="app-main">
    <div class="topbar">
        <div>
            <div class="topbar-title">API Sources</div>
            <div class="topbar-subtitle">Connect provider endpoints and monitor delivery health.</div>
        </div>
        <div class="topbar-actions">
            <div class="badge-pill">
                Active: <strong><?= (int)$pdo->query("SELECT COUNT(*) FROM api_sources WHERE status = 'on'")->fetchColumn() ?></strong>
            </div>
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
                <div class="card-title">Configured Sources</div>
            </div>
            <div class="table-responsive">
                <table class="table-glass">
                    <thead>
                    <tr>
                        <th>Name</th>
                        <th>URL</th>
                        <th>Interval</th>
                        <th>Status</th>
                        <th>Last Polled</th>
                        <th></th>
                    </tr>
                    </thead>
                    <tbody>
                    <?php if (!$sources): ?>
                        <tr>
                            <td colspan="6" class="text-center text-muted py-3">
                                No API sources configured yet.
                            </td>
                        </tr>
                    <?php else: ?>
                        <?php foreach ($sources as $src): ?>
                            <tr>
                                <td><?= htmlspecialchars($src['name']) ?></td>
                                <td style="max-width:250px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                                    <span title="<?= htmlspecialchars($src['url']) ?>">
                                        <?= htmlspecialchars($src['url']) ?>
                                    </span>
                                </td>
                                <td><?= (int)$src['poll_interval'] ?>s</td>
                                <td>
                                    <?php if ($src['status'] === 'on'): ?>
                                        <span class="badge badge-success">ON</span>
                                    <?php else: ?>
                                        <span class="badge badge-danger">OFF</span>
                                    <?php endif; ?>
                                </td>
                                <td><?= htmlspecialchars($src['last_polled_at'] ?? '-') ?></td>
                                <td class="text-end">
                                    <a href="?toggle=<?= (int)$src['id'] ?>" class="btn btn-xs btn-outline">
                                        Toggle
                                    </a>
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
                <div class="card-title">Add New API Source</div>
            </div>
            <form method="post" autocomplete="off">
                <input type="hidden" name="csrf_token" value="<?= htmlspecialchars(csrf_token()) ?>">
                <input type="hidden" name="action" value="create">
                <div class="form-group">
                    <label class="label">API Name</label>
                    <input type="text" name="name" class="input" required
                           placeholder="Refine Premium SMS">
                </div>
                <div class="form-group">
                    <label class="label">API URL</label>
                    <input type="url" name="url" id="api-url" class="input" required
                           placeholder="https://refinepremiumsms.xyz/con.php">
                </div>
                <div class="form-group">
                    <label class="label">Poll Interval (seconds)</label>
                    <input type="number" name="poll_interval" class="input" min="10" value="60">
                </div>
                <div class="form-group">
                    <label class="label">Status</label>
                    <select name="status" class="select">
                        <option value="on">ON</option>
                        <option value="off" selected>OFF</option>
                    </select>
                </div>

                <div class="d-flex align-items-center justify-content-between mt-2">
                    <button type="button" id="btn-test-api" class="btn btn-outline btn-xs">
                        Test API
                    </button>
                    <button type="submit" class="btn btn-primary btn-xs">
                        Add API Source
                    </button>
                </div>
            </form>
            <div id="test-api-result" class="mt-3" style="font-size:13px;"></div>
        </div>
    </div>
</div>

<?php include __DIR__ . '/includes/footer.php'; ?>