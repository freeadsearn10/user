<?php
require_once __DIR__ . '/../config/config.php';
require_admin();

global $pdo;

// Filters
$filters = [
    'user'    => trim($_GET['user'] ?? ''),
    'country' => trim($_GET['country'] ?? ''),
    'range'   => trim($_GET['range'] ?? ''),
    'sid'     => trim($_GET['sid'] ?? ''),
    'from'    => trim($_GET['from'] ?? ''),
    'to'      => trim($_GET['to'] ?? ''),
];

$where = [];
$params = [];

if ($filters['user'] !== '') {
    $where[] = 'u.username = :user';
    $params[':user'] = $filters['user'];
}
if ($filters['country'] !== '') {
    $where[] = 'sl.country = :country';
    $params[':country'] = $filters['country'];
}
if ($filters['range'] !== '') {
    $where[] = 'sl.range = :range';
    $params[':range'] = $filters['range'];
}
if ($filters['sid'] !== '') {
    $where[] = 'sl.sid = :sid';
    $params[':sid'] = $filters['sid'];
}
if ($filters['from'] !== '') {
    $where[] = 'DATE(sl.created_at) >= :from';
    $params[':from'] = $filters['from'];
}
if ($filters['to'] !== '') {
    $where[] = 'DATE(sl.created_at) <= :to';
    $params[':to'] = $filters['to'];
}

$whereSql = $where ? ('WHERE ' . implode(' AND ', $where)) : '';

// Export CSV
if (isset($_GET['export']) && $_GET['export'] === '1') {
    $stmt = $pdo->prepare("
        SELECT sl.*, u.username, s.name AS source_name
        FROM sms_logs sl
        LEFT JOIN users u ON sl.user_id = u.id
        LEFT JOIN api_sources s ON sl.api_source_id = s.id
        $whereSql
        ORDER BY sl.created_at DESC
    ");
    $stmt->execute($params);
    $rows = $stmt->fetchAll();

    header('Content-Type: text/csv');
    header('Content-Disposition: attachment; filename="sms_logs.csv"');

    $out = fopen('php://output', 'w');
    fputcsv($out, [
        'Date', 'Time', 'User', 'Number', 'Country', 'Range', 'SID',
        'Message', 'Carrier', 'Payout', 'API Source', 'Status',
    ]);

    foreach ($rows as $row) {
        $dt = new DateTime($row['created_at']);
        fputcsv($out, [
            $dt->format('Y-m-d'),
            $dt->format('H:i:s'),
            $row['username'] ?? '',
            $row['number'],
            $row['country'],
            $row['range'],
            $row['sid'],
            $row['message'],
            $row['carrier'],
            $row['payout'],
            $row['source_name'] ?? '',
            $row['status'],
        ]);
    }
    fclose($out);
    exit;
}

// Paginated view (latest 200)
$stmt = $pdo->prepare("
    SELECT sl.*, u.username, s.name AS source_name
    FROM sms_logs sl
    LEFT JOIN users u ON sl.user_id = u.id
    LEFT JOIN api_sources s ON sl.api_source_id = s.id
    $whereSql
    ORDER BY sl.created_at DESC
    LIMIT 200
");
$stmt->execute($params);
$logs = $stmt->fetchAll();

$page_title = 'SMS Logs (CDR)';
$active_nav = 'sms_logs';
include __DIR__ . '/includes/header.php';
include __DIR__ . '/includes/sidebar.php';
?>
<div class="app-main">
    <div class="topbar">
        <div>
            <div class="topbar-title">SMS Logs (CDR)</div>
            <div class="topbar-subtitle">Search and export OTP delivery records.</div>
        </div>
        <div class="topbar-actions">
            <a href="?export=1" class="btn btn-outline btn-xs">Export CSV</a>
        </div>
    </div>

    <div class="card mb-3">
        <form method="get" class="row g-2">
            <div class="col-md-2">
                <label class="label">User</label>
                <input type="text" name="user" class="input" value="<?= htmlspecialchars($filters['user']) ?>">
            </div>
            <div class="col-md-2">
                <label class="label">Country</label>
                <input type="text" name="country" class="input" value="<?= htmlspecialchars($filters['country']) ?>">
            </div>
            <div class="col-md-2">
                <label class="label">Range</label>
                <input type="text" name="range" class="input" value="<?= htmlspecialchars($filters['range']) ?>">
            </div>
            <div class="col-md-2">
                <label class="label">SID</label>
                <input type="text" name="sid" class="input" value="<?= htmlspecialchars($filters['sid']) ?>">
            </div>
            <div class="col-md-2">
                <label class="label">From</label>
                <input type="date" name="from" class="input" value="<?= htmlspecialchars($filters['from']) ?>">
            </div>
            <div class="col-md-2">
                <label class="label">To</label>
                <input type="date" name="to" class="input" value="<?= htmlspecialchars($filters['to']) ?>">
            </div>
            <div class="col-12 mt-2">
                <button type="submit" class="btn btn-primary btn-xs">Filter</button>
            </div>
        </form>
    </div>

    <div class="card">
        <div class="card-title-row">
            <div class="card-title">Latest 200 Logs</div>
        </div>
        <div class="table-responsive">
            <table class="table-glass">
                <thead>
                <tr>
                    <th>Date</th>
                    <th>Time</th>
                    <th>User</th>
                    <th>Number</th>
                    <th>Country</th>
                    <th>Range</th>
                    <th>SID</th>
                    <th>Message</th>
                    <th>Carrier</th>
                    <th>Payout</th>
                    <th>API Source</th>
                    <th>Status</th>
                </tr>
                </thead>
                <tbody>
                <?php if (!$logs): ?>
                    <tr>
                        <td colspan="12" class="text-center text-muted py-3">
                            No logs found for the selected filters.
                        </td>
                    </tr>
                <?php else: ?>
                    <?php foreach ($logs as $row): ?>
                        <?php $dt = new DateTime($row['created_at']); ?>
                        <tr>
                            <td><?= $dt->format('Y-m-d') ?></td>
                            <td><?= $dt->format('H:i:s') ?></td>
                            <td><?= htmlspecialchars($row['username'] ?? 'Unmatched') ?></td>
                            <td><?= htmlspecialchars($row['number']) ?></td>
                            <td><?= htmlspecialchars($row['country'] ?? '') ?></td>
                            <td><?= htmlspecialchars($row['range'] ?? '') ?></td>
                            <td><?= htmlspecialchars($row['sid'] ?? '') ?></td>
                            <td style="max-width:260px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                                title="<?= htmlspecialchars($row['message'] ?? '') ?>">
                                <?= htmlspecialchars($row['message'] ?? '') ?>
                            </td>
                            <td><?= htmlspecialchars($row['carrier'] ?? '') ?></td>
                            <td>$<?= fmt_amount($row['payout']) ?></td>
                            <td><?= htmlspecialchars($row['source_name'] ?? '') ?></td>
                            <td>
                                <?php
                                $status = $row['status'];
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

<?php include __DIR__ . '/includes/footer.php'; ?>