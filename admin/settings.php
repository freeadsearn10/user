<?php
require_once __DIR__ . '/../config/config.php';
require_admin();

$errors = [];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    verify_csrf();

    $system_name   = trim($_POST['system_name'] ?? '');
    $cron_interval = trim($_POST['cron_interval'] ?? '');
    $api_master_key = trim($_POST['api_master_key'] ?? '');
    $theme         = trim($_POST['theme'] ?? 'dark');

    if ($system_name === '') {
        $errors[] = 'System name is required.';
    }
    if ($cron_interval !== '' && (!ctype_digit($cron_interval) || (int)$cron_interval < 10)) {
        $errors[] = 'Cron interval must be at least 10 seconds.';
    }

    if (!$errors) {
        set_setting('system_name', $system_name);
        if ($cron_interval !== '') {
            set_setting('cron_interval', $cron_interval);
        }
        set_setting('api_master_key', $api_master_key);
        set_setting('theme', $theme);
        flash('success', 'Settings updated.');
        redirect('/admin/settings.php');
    }
}

$system_name   = get_setting('system_name', 'IPRN SMS Panel');
$cron_interval = get_setting('cron_interval', '60');
$api_master_key = get_setting('api_master_key', '');
$theme         = get_setting('theme', 'dark');

$page_title = 'Settings';
$active_nav = 'settings';
include __DIR__ . '/includes/header.php';
include __DIR__ . '/includes/sidebar.php';
?>
<div class="app-main">
    <div class="topbar">
        <div>
            <div class="topbar-title">System Settings</div>
            <div class="topbar-subtitle">Branding, cron security and theme.</div>
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

    <div class="card" style="max-width: 640px;">
        <div class="card-title-row">
            <div class="card-title">Core Settings</div>
        </div>
        <form method="post">
            <input type="hidden" name="csrf_token" value="<?= htmlspecialchars(csrf_token()) ?>">

            <div class="form-group">
                <label class="label">System Name</label>
                <input type="text" name="system_name" class="input" required
                       value="<?= htmlspecialchars($system_name) ?>">
            </div>
            <div class="form-group">
                <label class="label">Cron Interval (seconds)</label>
                <input type="number" name="cron_interval" class="input" min="10"
                       value="<?= htmlspecialchars($cron_interval) ?>">
                <small class="text-muted" style="font-size: 12px;">
                    Recommended: 30–120 seconds. Use this for your server's cron timing.
                </small>
            </div>
            <div class="form-group">
                <label class="label">API Master Key</label>
                <input type="text" name="api_master_key" class="input"
                       value="<?= htmlspecialchars($api_master_key) ?>">
                <small class="text-muted" style="font-size: 12px;">
                    This key secures the cron endpoint at <code>/api/fetch_logs.php?key=MASTER_KEY</code>.
                </small>
            </div>
            <div class="form-group">
                <label class="label">Theme</label>
                <select name="theme" class="select">
                    <option value="dark" <?= $theme === 'dark' ? 'selected' : '' ?>>Dark / Neon</option>
                    <option value="light" <?= $theme === 'light' ? 'selected' : '' ?>>Light</option>
                </select>
            </div>
            <div class="d-grid mt-2">
                <button type="submit" class="btn btn-primary btn-xs">
                    Save Settings
                </button>
            </div>
        </form>
    </div>
</div>

<?php include __DIR__ . '/includes/footer.php'; ?>