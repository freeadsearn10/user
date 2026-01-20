<?php
require_once __DIR__ . '/../config/config.php';
require_admin();

global $pdo;

// Handle approve / reject
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    verify_csrf();
    $action = $_POST['action'] ?? '';
    $id = (int)($_POST['id'] ?? 0);
    $note = trim($_POST['note'] ?? '');

    $stmt = $pdo->prepare("SELECT * FROM payouts WHERE id = ?");
    $stmt->execute([$id]);
    $payout = $stmt->fetch();

    if ($payout && $payout['status'] === 'pending') {
        $userId = (int)$payout['user_id'];
        $amount = (float)$payout['amount'];

        if ($action === 'approve') {
            // Deduct from balance and mark approved
            $pdo->beginTransaction();
            try {
                $stmtUpdate = $pdo->prepare("
                    UPDATE users SET balance = balance - :amount
                    WHERE id = :id AND balance >= :amount
                ");
                $stmtUpdate->execute([
                    ':amount' => $amount,
                    ':id'     => $userId,
                ]);

                if ($stmtUpdate->rowCount() === 0) {
                    throw new Exception('Insufficient balance to approve payout.');
                }

                $pdo->prepare("
                    UPDATE payouts
                    SET status = 'approved', admin_note = :note, processed_at = NOW()
                    WHERE id = :id
                ")->execute([
                    ':note' => $note,
                    ':id'   => $id,
                ]);

                $pdo->prepare("
                    INSERT INTO notifications (user_id, title, message, type, is_read, created_at)
                    VALUES (:user_id, :title, :message, 'payout', 0, NOW())
                ")->execute([
                    ':user_id' => $userId,
                    ':title'   => 'Payout approved',
                    ':message' => 'Your payout request of 
            $pdo->prepare("
                UPDATE payouts
                SET status = 'rejected', admin_note = :note, processed_at = NOW()
                WHERE id = :id
            ")->execute([
                ':note' => $note,
                ':id'   => $id,
            ]);

            $pdo->prepare("
                INSERT INTO notifications (user_id, title, message, type, is_read, created_at)
                VALUES (:user_id, :title, :message, 'payout', 0, NOW())
            ")->execute([
                ':user_id' => $userId,
                ':title'   => 'Payout rejected',
                ':message' => 'Your payout request of $' . number_format($amount, 4, '.', '') . ' has been rejected.',
            ]);

            flash('info', 'Payout rejected.');
        }
    }

    redirect('/admin/payouts.php');
}

// Fetch payouts
$pendingStmt = $pdo->query("
    SELECT p.*, u.username
    FROM payouts p
    JOIN users u ON p.user_id = u.id
    WHERE p.status = 'pending'
    ORDER BY p.requested_at ASC
");
$pending = $pendingStmt->fetchAll();

$historyStmt = $pdo->query("
    SELECT p.*, u.username
    FROM payouts p
    JOIN users u ON p.user_id = u.id
    WHERE p.status IN ('approved','rejected')
    ORDER BY p.processed_at DESC
    LIMIT 200
");
$history = $historyStmt->fetchAll();

$page_title = 'Payout Management';
$active_nav = 'payouts';
include __DIR__ . '/includes/header.php';
include __DIR__ . '/includes/sidebar.php';
?>
<div class="app-main">
    <div class="topbar">
        <div>
            <div class="topbar-title">Payout Management</div>
            <div class="topbar-subtitle">Review withdrawal requests and payment history.</div>
        </div>
    </div>

    <?php foreach (get_flashes() as $type => $messages): ?>
        <?php foreach ($messages as $msg): ?>
            <div class="alert alert-<?= htmlspecialchars($type) ?>">
                <?= htmlspecialchars($msg) ?>
            </div>
        <?php endforeach; ?>
    <?php endforeach; ?>

    <div class="grid" style="grid-template-columns: minmax(0, 1.4fr) minmax(0, 1.6fr); gap: 18px;">
        <div class="card">
            <div class="card-title-row">
                <div class="card-title">Pending Requests</div>
            </div>
            <div class="table-responsive">
                <table class="table-glass">
                    <thead>
                    <tr>
                        <th>User</th>
                        <th>Amount</th>
                        <th>Method</th>
                        <th>Destination</th>
                        <th>Requested</th>
                        <th></th>
                    </tr>
                    </thead>
                    <tbody>
                    <?php if (!$pending): ?>
                        <tr>
                            <td colspan="6" class="text-center text-muted py-3">
                                No pending payout requests.
                            </td>
                        </tr>
                    <?php else: ?>
                        <?php foreach ($pending as $p): ?>
                            <tr>
                                <td><?= htmlspecialchars($p['username']) ?></td>
                                <td>$<?= fmt_amount($p['amount']) ?></td>
                                <td><?= htmlspecialchars($p['method'] ?? '') ?></td>
                                <td><?= htmlspecialchars($p['destination'] ?? '') ?></td>
                                <td><?= htmlspecialchars($p['requested_at']) ?></td>
                                <td class="text-end">
                                    <form method="post" style="display:inline-block;">
                                        <input type="hidden" name="csrf_token" value="<?= htmlspecialchars(csrf_token()) ?>">
                                        <input type="hidden" name="id" value="<?= (int)$p['id'] ?>">
                                        <input type="hidden" name="note" value="">
                                        <button type="submit" name="action" value="approve"
                                                class="btn btn-primary btn-xs">
                                            Approve
                                        </button>
                                    </form>
                                    <form method="post" style="display:inline-block;"
                                          onsubmit="return confirm('Reject this payout?');">
                                        <input type="hidden" name="csrf_token" value="<?= htmlspecialchars(csrf_token()) ?>">
                                        <input type="hidden" name="id" value="<?= (int)$p['id'] ?>">
                                        <input type="hidden" name="note" value="">
                                        <button type="submit" name="action" value="reject"
                                                class="btn btn-outline btn-xs">
                                            Reject
                                        </button>
                                    </form>
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
                <div class="card-title">Payout History</div>
            </div>
            <div class="table-responsive">
                <table class="table-glass">
                    <thead>
                    <tr>
                        <th>User</th>
                        <th>Amount</th>
                        <th>Status</th>
                        <th>Requested</th>
                        <th>Processed</th>
                    </tr>
                    </thead>
                    <tbody>
                    <?php if (!$history): ?>
                        <tr>
                            <td colspan="5" class="text-center text-muted py-3">
                                No payout history yet.
                            </td>
                        </tr>
                    <?php else: ?>
                        <?php foreach ($history as $p): ?>
                            <tr>
                                <td><?= htmlspecialchars($p['username']) ?></td>
                                <td>$<?= fmt_amount($p['amount']) ?></td>
                                <td>
                                    <?php if ($p['status'] === 'approved'): ?>
                                        <span class="badge badge-success">Approved</span>
                                    <?php else: ?>
                                        <span class="badge badge-danger">Rejected</span>
                                    <?php endif; ?>
                                </td>
                                <td><?= htmlspecialchars($p['requested_at']) ?></td>
                                <td><?= htmlspecialchars($p['processed_at']) ?></td>
                            </tr>
                        <?php endforeach; ?>
                    <?php endif; ?>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<?php include __DIR__ . '/includes/footer.php'; ?> . number_format($amount, 4, '.', '') . ' has been approved.',
                ]);

                $pdo->commit();
                flash('success', 'Payout approved.');
            } catch (Throwable $e) {
                $pdo->rollBack();
                flash('danger', 'Error approving payout: ' . $e->getMessage());
            }
        } elseif ($action === 'reject') {
            $pdo->prepare("
                UPDATE payouts
                SET status = 'rejected', admin_note = :note, processed_at = NOW()
                WHERE id = :id
            ")->execute([
                ':note' => $note,
                ':id'   => $id,
            ]);

            $pdo->prepare("
                INSERT INTO notifications (user_id, title, message, type, is_read, created_at)
                VALUES (:user_id, :title, :message, 'payout', 0, NOW())
            ")->execute([
                ':user_id' => $userId,
                ':title'   => 'Payout rejected',
                ':message' => 'Your payout request of $' . number_format($amount, 4, '.', '') . ' has been rejected.',
            ]);

            flash('info', 'Payout rejected.');
        }
    }

    redirect('/admin/payouts.php');
}

// Fetch payouts
$pendingStmt = $pdo->query("
    SELECT p.*, u.username
    FROM payouts p
    JOIN users u ON p.user_id = u.id
    WHERE p.status = 'pending'
    ORDER BY p.requested_at ASC
");
$pending = $pendingStmt->fetchAll();

$historyStmt = $pdo->query("
    SELECT p.*, u.username
    FROM payouts p
    JOIN users u ON p.user_id = u.id
    WHERE p.status IN ('approved','rejected')
    ORDER BY p.processed_at DESC
    LIMIT 200
");
$history = $historyStmt->fetchAll();

$page_title = 'Payout Management';
$active_nav = 'payouts';
include __DIR__ . '/includes/header.php';
include __DIR__ . '/includes/sidebar.php';
?>
<div class="app-main">
    <div class="topbar">
        <div>
            <div class="topbar-title">Payout Management</div>
            <div class="topbar-subtitle">Review withdrawal requests and payment history.</div>
        </div>
    </div>

    <?php foreach (get_flashes() as $type => $messages): ?>
        <?php foreach ($messages as $msg): ?>
            <div class="alert alert-<?= htmlspecialchars($type) ?>">
                <?= htmlspecialchars($msg) ?>
            </div>
        <?php endforeach; ?>
    <?php endforeach; ?>

    <div class="grid" style="grid-template-columns: minmax(0, 1.4fr) minmax(0, 1.6fr); gap: 18px;">
        <div class="card">
            <div class="card-title-row">
                <div class="card-title">Pending Requests</div>
            </div>
            <div class="table-responsive">
                <table class="table-glass">
                    <thead>
                    <tr>
                        <th>User</th>
                        <th>Amount</th>
                        <th>Method</th>
                        <th>Destination</th>
                        <th>Requested</th>
                        <th></th>
                    </tr>
                    </thead>
                    <tbody>
                    <?php if (!$pending): ?>
                        <tr>
                            <td colspan="6" class="text-center text-muted py-3">
                                No pending payout requests.
                            </td>
                        </tr>
                    <?php else: ?>
                        <?php foreach ($pending as $p): ?>
                            <tr>
                                <td><?= htmlspecialchars($p['username']) ?></td>
                                <td>$<?= fmt_amount($p['amount']) ?></td>
                                <td><?= htmlspecialchars($p['method'] ?? '') ?></td>
                                <td><?= htmlspecialchars($p['destination'] ?? '') ?></td>
                                <td><?= htmlspecialchars($p['requested_at']) ?></td>
                                <td class="text-end">
                                    <form method="post" style="display:inline-block;">
                                        <input type="hidden" name="csrf_token" value="<?= htmlspecialchars(csrf_token()) ?>">
                                        <input type="hidden" name="id" value="<?= (int)$p['id'] ?>">
                                        <input type="hidden" name="note" value="">
                                        <button type="submit" name="action" value="approve"
                                                class="btn btn-primary btn-xs">
                                            Approve
                                        </button>
                                    </form>
                                    <form method="post" style="display:inline-block;"
                                          onsubmit="return confirm('Reject this payout?');">
                                        <input type="hidden" name="csrf_token" value="<?= htmlspecialchars(csrf_token()) ?>">
                                        <input type="hidden" name="id" value="<?= (int)$p['id'] ?>">
                                        <input type="hidden" name="note" value="">
                                        <button type="submit" name="action" value="reject"
                                                class="btn btn-outline btn-xs">
                                            Reject
                                        </button>
                                    </form>
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
                <div class="card-title">Payout History</div>
            </div>
            <div class="table-responsive">
                <table class="table-glass">
                    <thead>
                    <tr>
                        <th>User</th>
                        <th>Amount</th>
                        <th>Status</th>
                        <th>Requested</th>
                        <th>Processed</th>
                    </tr>
                    </thead>
                    <tbody>
                    <?php if (!$history): ?>
                        <tr>
                            <td colspan="5" class="text-center text-muted py-3">
                                No payout history yet.
                            </td>
                        </tr>
                    <?php else: ?>
                        <?php foreach ($history as $p): ?>
                            <tr>
                                <td><?= htmlspecialchars($p['username']) ?></td>
                                <td>$<?= fmt_amount($p['amount']) ?></td>
                                <td>
                                    <?php if ($p['status'] === 'approved'): ?>
                                        <span class="badge badge-success">Approved</span>
                                    <?php else: ?>
                                        <span class="badge badge-danger">Rejected</span>
                                    <?php endif; ?>
                                </td>
                                <td><?= htmlspecialchars($p['requested_at']) ?></td>
                                <td><?= htmlspecialchars($p['processed_at']) ?></td>
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