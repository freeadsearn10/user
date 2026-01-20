<?php
require_once __DIR__ . '/../config/config.php';
require_user();

global $pdo;
$user = current_user();
$userId = (int)$user['id'];

// Mark all as read when page is loaded
$pdo->prepare("UPDATE notifications SET is_read = 1 WHERE user_id = :uid")->execute([':uid' => $userId]);

$stmt = $pdo->prepare("
    SELECT *
    FROM notifications
    WHERE user_id = :uid OR user_id IS NULL
    ORDER BY created_at DESC
    LIMIT 100
");
$stmt->execute([':uid' => $userId]);
$notifications = $stmt->fetchAll();

$page_title = 'Notifications';
$active_nav = 'notifications';
include __DIR__ . '/includes/header.php';
include __DIR__ . '/includes/sidebar.php';
?>
<div class="app-main">
    <div class="topbar">
        <div>
            <div class="topbar-title">Notifications</div>
            <div class="topbar-subtitle">
                Route changes, payouts and system alerts.
            </div>
        </div>
    </div>

    <div class="card">
        <div class="card-title-row">
            <div class="card-title">Latest Notifications</div>
        </div>
        <div class="table-responsive">
            <table class="table-glass">
                <thead>
                <tr>
                    <th>Time</th>
                    <th>Type</th>
                    <th>Title</th>
                    <th>Message</th>
                </tr>
                </thead>
                <tbody>
                <?php if (!$notifications): ?>
                    <tr>
                        <td colspan="4" class="text-center text-muted py-3">
                            No notifications yet.
                        </td>
                    </tr>
                <?php else: ?>
                    <?php foreach ($notifications as $n): ?>
                        <tr>
                            <td><?= htmlspecialchars($n['created_at']) ?></td>
                            <td><?= htmlspecialchars(ucfirst($n['type'])) ?></td>
                            <td><?= htmlspecialchars($n['title']) ?></td>
                            <td><?= htmlspecialchars($n['message']) ?></td>
                        </tr>
                    <?php endforeach; ?>
                <?php endif; ?>
                </tbody>
            </table>
        </div>
    </div>
</div>

<?php include __DIR__ . '/includes/footer.php'; ?>