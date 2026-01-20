<?php
require_once __DIR__ . '/../config/config.php';
require_user();

global $pdo;
$user = current_user();
$userId = (int)$user['id'];

$errors = [];

// Handle new payout request
if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'request') {
    verify_csrf();

    $amount = (float)($_POST['amount'] ?? 0);
    $method = trim($_POST['method'] ?? '');
    $destination = trim($_POST['destination'] ?? '');

    $minWithdrawal = 1.0; // configurable minimum
    if ($amount < $minWithdrawal) {
        $errors[] = 'Minimum withdrawal is $' . number_format($minWithdrawal, 2);
    }
    if ($amount > (float)$user['balance']) {
        $errors[] = 'Requested amount exceeds your current balance.';
    }
    if ($method === '') {
        $errors[] = 'Payment method is required.';
    }
    if ($destination === '') {
        $errors[] = 'Destination / wallet ID is required.';
    }

    if (!$errors) {
        $stmt = $pdo->prepare("
            INSERT INTO payouts (user_id, amount, status, method, destination, requested_at)
            VALUES (:uid, :amount, 'pending', :method, :destination, NOW())
        ");
        $stmt->execute([
            ':uid'        => $userId,
            ':amount'     => $amount,
            ':method'     => $method,
            ':destination'=> $destination,
        ]);
        flash('success', 'Payout request submitted.');
        redirect('/user/payouts.php');
    }
}

// Fetch payouts
$stmt = $pdo->prepare("
    SELECT * FROM payouts
    WHERE user_id = :uid
    ORDER BY requested_at DESC
");
$stmt->execute([':uid' => $userId]);
$payouts = $stmt->fetchAll();

$page_title = 'Payouts';
$active_nav = 'payouts';
include __DIR__ . '/includes/header.php';
include __DIR__ . '/includes/sidebar.php';
?>
<div class="app-main">
    <div class="topbar">
        <div>
            <div class="topbar-title">Payouts</div>
            <div class="topbar-subtitle">
                Request withdrawals and track your payment history.
            </div>
        </div>
        <div class="topbar-actions">
            <div class="badge-pill">
                Current Balance: <strong>$<?= fmt_amount($user['balance']) ?></strong>
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

    <div class="grid" style="grid-template-columns: minmax(0, 1.2fr) minmax(0, 1.8fr); gap: 18px;">
        <div class="card">
            <div class="card-title-row">
                <div class="card-title">Request Payout</div>
            </div>
            <form method="post">
                <input type="hidden" name="csrf_token" value="<?= htmlspecialchars(csrf_token()) ?>">
                <input type="hidden" name="action" value="request">

                <div class="form-group">
                    <label class="label">Amount (USD)</label>
                    <input type="number" step="0.0001" name="amount" class="input"
                           value="<?= htmlspecialchars($_POST['amount'] ?? '') ?>">
                </div>
                <div class="form-group">
                    <label class="label">Payment Method</label>
                    <input type="text" name="method" class="input"
                           placeholder="Binance, USDT, Bank, etc."
                           value="<?= htmlspecialchars($_POST['method'] ?? '') ?>">
                </div>
                <div class="form-group">
                    <label class="label">Destination / Wallet ID</label>
                    <input type="text" name="destination" class="input"
                           value="<?= htmlspecialchars($_POST['destination'] ?? '') ?>">
                </div>
                <div class="d-grid mt-2">
                    <button type="submit" class="btn btn-primary btn-xs">
                        Submit Request
                    </button>
                </div>
                <p class="text-muted mt-2" style="font-size: 12px;">
                    Minimum withdrawal is $<?= number_format($minWithdrawal, 2) ?>. Requests are usually processed within 24 hours.
                </p>
            </form>
        </div>

        <div class="card">
            <div class="card-title-row">
                <div class="card-title">Payout History</div>
            </div>
            <div class="table-responsive">
                <table class="table-glass">
                    <thead>
                    <tr>
                        <th>Amount</th>
                        <th>Status</th>
                        <th>Method</th>
                        <th>Destination</th>
                        <th>Requested</th>
                        <th>Processed</th>
                    </tr>
                    </thead>
                    <tbody>
                    <?php if (!$payouts): ?>
                        <tr>
                            <td colspan="6" class="text-center text-muted py-3">
                                No payout requests yet.
                            </td>
                        </tr>
                    <?php else: ?>
                        <?php foreach ($payouts as $p): ?>
                            <tr>
                                <td>$<?= fmt_amount($p['amount']) ?></td>
                                <td>
                                    <?php if ($p['status'] === 'pending'): ?>
                                        <span class="badge badge-warning">Pending</span>
                                    <?php elseif ($p['status'] === 'approved'): ?>
                                        <span class="badge badge-success">Approved</span>
                                    <?php else: ?>
                                        <span class="badge badge-danger">Rejected</span>
                                    <?php endif; ?>
                                </td>
                                <td><?= htmlspecialchars($p['method'] ?? '') ?></td>
                                <td><?= htmlspecialchars($p['destination'] ?? '') ?></td>
                                <td><?= htmlspecialchars($p['requested_at']) ?></td>
                                <td><?= htmlspecialchars($p['processed_at'] ?? '-') ?></td>
                            </tr>
                        <?php endforeach; ?>
                    <?php endif; ?>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<?php include __DIR__ . '/includes/footer.php'; ?>