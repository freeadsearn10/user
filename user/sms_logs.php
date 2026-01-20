<?php
require_once __DIR__ . '/../config/config.php';
require_user();

$user = current_user();
$page_title = 'Live SMS Logs';
$active_nav = 'sms_logs';
include __DIR__ . '/includes/header.php';
include __DIR__ . '/includes/sidebar.php';
?>
<div class="app-main">
    <div class="topbar">
        <div>
            <div class="topbar-title">Live SMS Logs</div>
            <div class="topbar-subtitle">
                Real-time OTP traffic for your assigned numbers. Auto-refresh every 5 seconds.
            </div>
        </div>
    </div>

    <div class="card">
        <div class="card-title-row">
            <div class="card-title">Latest 100 OTP Logs</div>
        </div>
        <div id="live-logs">
            <div class="skeleton" style="height:220px;border-radius:14px;"></div>
        </div>
    </div>
</div>

<script>
    document.addEventListener('DOMContentLoaded', function () {
        setupAutoRefresh('/user/ajax_sms_logs.php', 'live-logs', 5000);
    });
</script>

<?php include __DIR__ . '/includes/footer.php'; ?>