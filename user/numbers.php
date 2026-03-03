<?php
require_once __DIR__ . '/../config/config.php';
require_user();

global $pdo;
$user = current_user();
$userId = (int)$user['id'];

$stmt = $pdo->prepare("
    SELECT av.number, av.country, av.range_name, av.otp_rate, rt.name AS route_name
    FROM assigned_numbers an
    JOIN available_numbers av ON an.number_id = av.id
    LEFT JOIN routes rt ON av.route_id = rt.id
    WHERE an.user_id = :uid
    ORDER BY av.country, av.range_name, av.number
");
$stmt->execute([':uid' => $userId]);
$numbers = $stmt->fetchAll();

$page_title = 'My Numbers';
$active_nav = 'numbers';
include __DIR__ . '/includes/header.php';
include __DIR__ . '/includes/sidebar.php';
?>
<div class="app-main">
    <div class="topbar">
        <div>
            <div class="topbar-title">My Numbers</div>
            <div class="topbar-subtitle">
                All premium SMS numbers assigned to your account.
            </div>
        </div>
    </div>

    <div class="card">
        <div class="card-title-row">
            <div class="card-title">Assigned Numbers</div>
        </div>
        <div class="table-responsive">
            <table class="table-glass">
                <thead>
                <tr>
                    <th>Number</th>
                    <th>Country</th>
                    <th>Range</th>
                    <th>Route</th>
                    <th>Rate / OTP</th>
                </tr>
                </thead>
                <tbody>
                <?php if (!$numbers): ?>
                    <tr>
                        <td colspan="5" class="text-center text-muted py-3">
                            No numbers assigned yet. Contact admin to get numbers.
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
                        </tr>
                    <?php endforeach; ?>
                <?php endif; ?>
                </tbody>
            </table>
        </div>
    </div>
</div>

<?php include __DIR__ . '/includes/footer.php'; ?>