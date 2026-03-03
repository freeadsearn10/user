<?php
require_once __DIR__ . '/../config/config.php';
require_user();

global $pdo;
$user = current_user();
$userId = (int)$user['id'];

// Stats: today SMS and revenue
$stmt = $pdo->prepare("
    SELECT COUNT(*) AS c, IFNULL(SUM(payout),0) AS r
    FROM sms_logs
    WHERE user_id = :uid AND DATE(created_at) = CURDATE()
");
$stmt->execute([':uid' => $userId]);
$rowToday = $stmt->fetch() ?: ['c' => 0, 'r' => 0];
$todaySms = (int)$rowToday['c'];
$todayRevenue = (float)$rowToday['r'];

$stmt = $pdo->prepare("
    SELECT COUNT(*) AS c, IFNULL(SUM(payout),0) AS r
    FROM sms_logs
    WHERE user_id = :uid AND created_at >= (NOW() - INTERVAL 1 HOUR)
");
$stmt->execute([':uid' => $userId]);
$rowHour = $stmt->fetch() ?: ['c' => 0, 'r' => 0];
$hourSms = (int)$rowHour['c'];

$numbersCount = (int)$pdo->prepare("
    SELECT COUNT(*) FROM assigned_numbers WHERE user_id = :uid
");
$numbersStmt = $pdo->prepare("SELECT COUNT(*) FROM assigned_numbers WHERE user_id = :uid");
$numbersStmt->execute([':uid' => $userId]);
$numbersCount = (int)$numbersStmt->fetchColumn();

// Latest logs
$stmt = $pdo->prepare("
    SELECT * FROM sms_logs
    WHERE user_id = :uid
    ORDER BY created_at DESC
    LIMIT 10
");
$stmt->execute([':uid' => $userId]);
$latestLogs = $stmt->fetchAll();

// 24h charts (per hour)
$labels = [];
$smsCounts = [];
$revenuePoints = [];

for ($i = 23; $i >= 0; $i--) {
    $from = new DateTime("-{$i} hour");
    $to = clone $from;
    $to->modify('+1 hour');

    $labels[] = $from->format('H:00');

    $stmt = $pdo->prepare("
        SELECT COUNT(*) AS c, IFNULL(SUM(payout),0) AS r
        FROM sms_logs
        WHERE user_id = :uid
          AND created_at >= :from
          AND created_at < :to
    ");
    $stmt->execute([
        ':uid'  => $userId,
        ':from' => $from->format('Y-m-d H:i:s'),
        ':to'   => $to->format('Y-m-d H:i:s'),
    ]);
    $row = $stmt->fetch() ?: ['c' => 0, 'r' => 0];
    $smsCounts[] = (int)$row['c'];
    $revenuePoints[] = (float)$row['r'];
}

$page_title = 'User Dashboard';
$active_nav = 'dashboard';
include __DIR__ . '/includes/header.php';
include __DIR__ . '/includes/sidebar.php';
?>
<div class="app-main">
    <div class="topbar">
        <div>
            <div class="topbar-title">Welcome, <?= htmlspecialchars($user['username']) ?></div>
            <div class="topbar-subtitle">
                Track your live OTP traffic, performance and payouts.
            </div>
        </div>
        <div class="topbar-actions">
            <div class="badge-pill">
                Balance: <strong>$<?= fmt_amount($user['balance']) ?></strong>
            </div>
        </div>
    </div>

    <div class="grid grid-4 mb-3">
        <div class="card">
            <div class="card-title-row">
                <div class="card-title">Today SMS</div>
            </div>
            <div class="card-metric-main"><?= number_format($todaySms) ?></div>
            <div class="card-metric-sub">Messages received today</div>
        </div>
        <div class="card">
            <div class="card-title-row">
                <div class="card-title">Today Revenue</div>
            </div>
            <div class="card-metric-main">$<?= fmt_amount($todayRevenue) ?></div>
            <div class="card-metric-sub">Total payout for today</div>
        </div>
        <div class="card">
            <div class="card-title-row">
                <div class="card-title">Last Hour SMS</div>
            </div>
            <div class="card-metric-main"><?= number_format($hourSms) ?></div>
            <div class="card-metric-sub">Messages in the last 60 minutes</div>
        </div>
        <div class="card">
            <div class="card-title-row">
                <div class="card-title">Assigned Numbers</div>
            </div>
            <div class="card-metric-main"><?= number_format($numbersCount) ?></div>
            <div class="card-metric-sub">Numbers available for monetization</div>
        </div>
    </div>

    <div class="grid" style="grid-template-columns: minmax(0, 1.7fr) minmax(0, 1.3fr); gap: 18px;">
        <div class="card">
            <div class="card-title-row">
                <div class="card-title">24h SMS Volume</div>
            </div>
            <div class="chart-container">
                <canvas id="chart-user-sms"></canvas>
            </div>
        </div>
        <div class="card">
            <div class="card-title-row">
                <div class="card-title">24h Revenue</div>
            </div>
            <div class="chart-container">
                <canvas id="chart-user-revenue"></canvas>
            </div>
        </div>
    </div>

    <div class="card mt-3">
        <div class="card-title-row">
            <div class="card-title">Latest OTP Logs</div>
        </div>
        <div class="table-responsive">
            <table class="table-glass">
                <thead>
                <tr>
                    <th>Date</th>
                    <th>SID</th>
                    <th>Number</th>
                    <th>Range</th>
                    <th>Country</th>
                    <th>Carrier</th>
                    <th>Payout</th>
                </tr>
                </thead>
                <tbody>
                <?php if (!$latestLogs): ?>
                    <tr>
                        <td colspan="7" class="text-center text-muted py-3">
                            No logs yet. As soon as traffic starts, OTPs will appear here.
                        </td>
                    </tr>
                <?php else: ?>
                    <?php foreach ($latestLogs as $log): ?>
                        <?php $dt = new DateTime($log['created_at']); ?>
                        <tr>
                            <td><?= $dt->format('Y-m-d H:i:s') ?></td>
                            <td><?= htmlspecialchars($log['sid'] ?? '') ?></td>
                            <td><?= htmlspecialchars($log['number']) ?></td>
                            <td><?= htmlspecialchars($log['range'] ?? '') ?></td>
                            <td><?= htmlspecialchars($log['country'] ?? '') ?></td>
                            <td><?= htmlspecialchars($log['carrier'] ?? '') ?></td>
                            <td>$<?= fmt_amount($log['payout']) ?></td>
                        </tr>
                    <?php endforeach; ?>
                <?php endif; ?>
                </tbody>
            </table>
        </div>
    </div>
</div>

<script>
    (function () {
        var labels = <?= json_encode($labels, JSON_UNESCAPED_UNICODE) ?>;
        var smsData = <?= json_encode($smsCounts, JSON_UNESCAPED_UNICODE) ?>;
        var revenueData = <?= json_encode($revenuePoints, JSON_UNESCAPED_UNICODE) ?>;

        document.addEventListener('DOMContentLoaded', function () {
            initLineChart('chart-user-sms', labels, smsData, 'SMS', '#38bdf8');
            initLineChart('chart-user-revenue', labels, revenueData, 'Revenue', '#22c55e');
        });
    })();
</script>

<?php include __DIR__ . '/includes/footer.php'; ?>