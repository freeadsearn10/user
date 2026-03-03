<?php
require_once __DIR__ . '/../config/config.php';
require_user();

global $pdo;
$user = current_user();
$userId = (int)$user['id'];

$stmt = $pdo->prepare("
    SELECT *
    FROM sms_logs
    WHERE user_id = :uid
    ORDER BY created_at DESC
    LIMIT 100
");
$stmt->execute([':uid' => $userId]);
$logs = $stmt->fetchAll();
?>
<div class="table-responsive">
    <table class="table-glass">
        <thead>
        <tr>
            <th>Date</th>
            <th>SID</th>
            <th>OTP Content</th>
            <th>Range</th>
            <th>Country</th>
            <th>Carrier</th>
            <th>Number</th>
            <th>Payout</th>
        </tr>
        </thead>
        <tbody>
        <?php if (!$logs): ?>
            <tr>
                <td colspan="8" class="text-center text-muted py-3">
                    Waiting for traffic. When SMS arrives, it will appear here instantly.
                </td>
            </tr>
        <?php else: ?>
            <?php foreach ($logs as $log): ?>
                <?php $dt = new DateTime($log['created_at']); ?>
                <tr>
                    <td><?= $dt->format('Y-m-d H:i:s') ?></td>
                    <td><?= htmlspecialchars($log['sid'] ?? '') ?></td>
                    <td style="max-width:260px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                        title="<?= htmlspecialchars($log['message'] ?? '') ?>">
                        <?= htmlspecialchars($log['message'] ?? '') ?>
                    </td>
                    <td><?= htmlspecialchars($log['range'] ?? '') ?></td>
                    <td><?= htmlspecialchars($log['country'] ?? '') ?></td>
                    <td><?= htmlspecialchars($log['carrier'] ?? '') ?></td>
                    <td><?= htmlspecialchars($log['number']) ?></td>
                    <td>$<?= fmt_amount($log['payout']) ?></td>
                </tr>
            <?php endforeach; ?>
        <?php endif; ?>
        </tbody>
    </table>
</div>