<?php
require_once __DIR__ . '/../config/config.php';
require_admin();

global $pdo;

// Summary stats
$totalUsers = (int)$pdo->query("SELECT COUNT(*) FROM users WHERE role = 'user'")->fetchColumn();
$totalAssigned = (int)$pdo->query("SELECT COUNT(*) FROM assigned_numbers")->fetchColumn();
$todaySms = (int)$pdo->query("SELECT COUNT(*) FROM sms_logs WHERE DATE(created_at) = CURDATE()")->fetchColumn();
$todayRevenue = (float)$pdo->query("SELECT IFNULL(SUM(payout), 0) FROM sms_logs WHERE DATE(created_at) = CURDATE()")->fetchColumn();
$activeApis = (int)$pdo->query("SELECT COUNT(*) FROM api_sources WHERE status = 'on'")->fetchColumn();

// Latest logs
$stmt = $pdo->prepare("
    SELECT sl.*, u.username, s.name AS source_name
    FROM sms_logs sl
    LEFT JOIN users u ON sl.user_id = u.id
    LEFT JOIN api_sources s ON sl.api_source_id = s.id
    ORDER BY sl.created_at DESC
    LIMIT 10
");
$stmt->execute();
$latestLogs = $stmt->fetchAll();

// Charts: last 7 days
$labels = [];
$smsCounts = [];
$revenuePoints = [];

for ($i = 6; $i >= 0; $i--) {
    $date = (new DateTime())->modify("-{$i} days")->format('Y-m-d');
    $labels[] = date('M j', strtotime($date));

    $stmt = $pdo->prepare("SELECT COUNT(*) AS c, IFNULL(SUM(payout),0) AS r FROM sms_logs WHERE DATE(created_at) = ?");
    $stmt->execute([$date]);
    $row = $stmt->fetch() ?: ['c' => 0, 'r' => 0];

    $smsCounts[] = (int)$row['c'];
    $revenuePoints[] = (float)$row['r'];
}

$page_title = 'Admin Dashboard';
$active_nav = 'dashboard';
include __DIR__ . '/includes/header.php';
include __DIR__ . '/includes/sidebar.php';

$systemName = get_setting('system_name', 'IPRN SMS Panel');
?>
<div class="app-main">
    <div class="topbar">
        <div>
            <div class="topbar-title"><?= htmlspecialchars($systemName) ?></div>
            <div class="topbar-subtitle">Traffic overview, revenue and live OTP logs</div>
        </div>
        <div class="topbar-actions">
            <div class="badge-pill">
                Active APIs: <strong><?= $activeApis ?></strong>
            </div>
        </div>
    </div>

    <div class="grid grid-4 mb-3">
        <div class="card">
            <div class="card-title-row">
                <div class="card-title">Total Users</div>
                <span class="badge badge-info">Teams</span>
            </div>
            <div class="card-metric-main"><?= number_format($totalUsers) ?></div>
            <div class="card-metric-sub">Registered monetization partners</div>
        </div>
        <div class="card">
            <div class="card-title-row">
                <div class="card-title">Assigned Numbers</div>
                <span class="badge badge-info">Live</span>
            </div>
            <div class="card-metric-main"><?= number_format($totalAssigned) ?></div>
            <div class="card-metric-sub">Numbers distributed to users</div>
        </div>
        <div class="card">
            <div class="card-title-row">
                <div class="card-title">Today SMS</div>
                <span class="badge badge-success">Last 24h</span>
            </div>
            <div class="card-metric-main"><?= number_format($todaySms) ?></div>
            <div class="card-metric-sub">Messages received from all APIs</div>
        </div>
        <div class="card">
            <div class="card-title-row">
                <div class="card-title">Today Revenue</div>
                <span class="badge badge-success">USD</span>
            </div>
            <div class="card-metric-main">$<?= fmt_amount($todayRevenue) ?></div>
            <div class="card-metric-sub">Total payouts generated today</div>
        </div>
    </div>

    <div class="grid" style="grid-template-columns: minmax(0, 2.1fr) minmax(0, 1.4fr); gap: 18px;">
        <div class="card">
            <div class="card-title-row">
                <div class="card-title">7-Day SMS Volume</div>
            </div>
            <div class="chart-container">
                <canvas id="chart-sms"></canvas>
            </div>
        </div>
        <div class="card">
            <div class="card-title-row">
                <div class="card-title">7-Day Revenue</div>
            </div>
            <div class="chart-container">
                <canvas id="chart-revenue"></canvas>
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
                    <th>User</th>
                    <th>Number</th>
                    <th>SID</th>
                    <th>Country</th>
                    <th>Carrier</th>
                    <th>Range</th>
                    <th>Payout</th>
                    <th>Status</th>
                </tr>
                </thead>
                <tbody>
                <?php if (!$latestLogs): ?>
                    <tr>
                        <td colspan="9" class="text-center text-muted py-3">
                            No SMS logs yet.
                        </td>
                    </tr>
                <?php else: ?>
                    <?php foreach ($latestLogs as $log): ?>
                        <tr>
                            <td><?= htmlspecialchars($log['created_at']) ?></td>
                            <td><?= htmlspecialchars($log['username'] ?? 'Unmatched') ?></td>
                            <td><?= htmlspecialchars($log['number']) ?></td>
                            <td><?= htmlspecialchars($log['sid'] ?? '') ?></td>
                            <td><?= htmlspecialchars($log['country'] ?? '') ?></td>
                            <td><?= htmlspecialchars($log['carrier'] ?? '') ?></td>
                            <td><?= htmlspecialchars($log['range'] ?? '') ?></td>
                            <td>$<?= fmt_amount($log['payout']) ?></td>
                            <td>
                                <?php
                                $status = $log['status'];
                                $badgeClass = 'badge-info';
                                if ($status === 'delivered') {
                                    $badgeClass = 'badge-success';
                                } elseif ($status === 'failed') {
                                    $badgeClass = 'badge-danger';
                                } elseif ($status === 'unmatched') {
                                    $badgeClass = 'badge-warning';
                                }
                                ?>
                                <span class="badge <?= $badgeClass ?>">
                                    <?= htmlspecialchars(ucfirst($status)) ?>
                                </span>
                            </td>
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
            initLineChart('chart-sms', labels, smsData, 'SMS', '#38bdf8');
            initLineChart('chart-revenue', labels, revenueData, 'Revenue', '#22c55e');
        });
    })();
</script>

<?php include __DIR__ . '/includes/footer.php'; ?>