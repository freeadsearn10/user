<?php
require_once __DIR__ . '/../config/config.php';
require_user();

global $pdo;
$user = current_user();
$userId = (int)$user['id'];

// Refresh API key (optional action)
if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'regen_key') {
    verify_csrf();
    $newKey = generate_api_key();
    $stmt = $pdo->prepare("UPDATE users SET api_key = :key WHERE id = :id");
    $stmt->execute([
        ':key' => $newKey,
        ':id'  => $userId,
    ]);
    $_SESSION['flash'] = ['success' => ['API key regenerated.']];
    $user['api_key'] = $newKey;
}

$apiKey = $user['api_key'];
$callbackExample = 'https://your-domain.com/your-endpoint';
$panelEndpoint = 'https://your-domain.com/api/user_logs.php';

$page_title = 'API Settings';
$active_nav = 'api';
include __DIR__ . '/includes/header.php';
include __DIR__ . '/includes/sidebar.php';
?>
<div class="app-main">
    <div class="topbar">
        <div>
            <div class="topbar-title">API Settings</div>
            <div class="topbar-subtitle">
                Integrate your own system and receive OTP logs programmatically.
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

    <div class="card mb-3">
        <div class="card-title-row">
            <div class="card-title">Your API Key</div>
        </div>
        <div class="form-group">
            <label class="label">API Key</label>
            <input type="text" class="input" readonly value="<?= htmlspecialchars($apiKey) ?>">
        </div>
        <form method="post" class="mt-2">
            <input type="hidden" name="csrf_token" value="<?= htmlspecialchars(csrf_token()) ?>">
            <input type="hidden" name="action" value="regen_key">
            <button type="submit" class="btn btn-outline btn-xs">
                Regenerate Key
            </button>
        </form>
        <p class="text-muted mt-2" style="font-size:12px;">
            Keep this key secret. Use it in your server-side integration to pull logs.
        </p>
    </div>

    <div class="card">
        <div class="card-title-row">
            <div class="card-title">Pull API Documentation</div>
        </div>
        <p class="mb-1" style="font-size: 13px;">
            Use HTTP GET to pull your latest OTP logs from the panel:
        </p>
        <pre style="font-size:12px;background:rgba(15,23,42,0.9);padding:10px;border-radius:10px;border:1px solid rgba(148,163,184,0.4);">
GET <?= htmlspecialchars($panelEndpoint) ?>?api_key=<?= htmlspecialchars($apiKey) ?>&amp;limit=50
        </pre>
        <p class="mb-1" style="font-size: 13px;">
            Optional query parameters:
        </p>
        <ul style="font-size: 13px;">
            <li><code>limit</code> – max logs to return (default 50, max 200)</li>
            <li><code>since_id</code> – return logs with ID &gt; given value (for incremental sync)</li>
        </ul>

        <p class="mb-1" style="font-size: 13px;">
            Example JSON response:
        </p>
<pre style="font-size:12px;background:rgba(15,23,42,0.9);padding:10px;border-radius:10px;border:1px solid rgba(148,163,184,0.4);">
{
  "success": true,
  "data": [
    {
      "id": 123,
      "created_at": "2025-01-01 12:00:01",
      "time": "12:00:01",
      "sid": "Facebook",
      "message": "****** is your code...",
      "number": "2250758467XXX",
      "range": "22507584",
      "country": "Ivory Coast",
      "carrier": "Orange",
      "payout": 0.2500
    }
  ]
}
</pre>

        <p class="mb-1" style="font-size: 13px;">
            You can store the <code>id</code> of the last processed log on your side and call again with
            <code>?since_id=LAST_ID</code> to receive only new logs.
        </p>

        <hr class="my-3">

        <div class="card-title-row">
            <div class="card-title">Callback Pattern (Example)</div>
        </div>
        <p class="mb-1" style="font-size: 13px;">
            You can optionally build your own callback endpoint that accepts this JSON format
            when you push data from the panel or from your own polling script:
        </p>
<pre style="font-size:12px;background:rgba(15,23,42,0.9);padding:10px;border-radius:10px;border:1px solid rgba(148,163,184,0.4);">
POST <?= htmlspecialchars($callbackExample) ?>

{
  "api_key": "<?= htmlspecialchars($apiKey) ?>",
  "log": {
    "id": 123,
    "time": "12:00:01",
    "sid": "Facebook",
    "message": "****** is your code...",
    "number": "2250758467XXX",
    "range": "22507584",
    "country": "Ivory Coast",
    "carrier": "Orange",
    "payout": 0.2500
  }
}
</pre>
    </div>
</div>

<?php include __DIR__ . '/includes/footer.php'; ?>