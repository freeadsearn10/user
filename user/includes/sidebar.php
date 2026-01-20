<?php
$active_nav = $active_nav ?? '';
$user = current_user();
$system_name = get_setting('system_name', 'IPRN SMS Panel');
?>
<aside class="app-sidebar">
    <div class="brand">
        <div class="brand-logo">U</div>
        <div class="brand-text">
            <div class="brand-title"><?= htmlspecialchars($system_name) ?></div>
            <div class="brand-subtitle">User Panel</div>
        </div>
    </div>

    <div class="mb-3 small text-muted">
        Logged in as<br>
        <strong><?= htmlspecialchars($user['username'] ?? '') ?></strong>
    </div>

    <div class="nav-section-label">Overview</div>
    <ul class="nav-list">
        <li class="nav-item">
            <a href="/user/dashboard.php" class="nav-link <?= $active_nav === 'dashboard' ? 'active' : '' ?>">
                <span class="nav-link-icon">📊</span>
                <span>Dashboard</span>
            </a>
        </li>
    </ul>

    <div class="nav-section-label">Traffic</div>
    <ul class="nav-list">
        <li class="nav-item">
            <a href="/user/sms_logs.php" class="nav-link <?= $active_nav === 'sms_logs' ? 'active' : '' ?>">
                <span class="nav-link-icon">📩</span>
                <span>Live SMS Logs</span>
            </a>
        </li>
        <li class="nav-item">
            <a href="/user/numbers.php" class="nav-link <?= $active_nav === 'numbers' ? 'active' : '' ?>">
                <span class="nav-link-icon">🔢</span>
                <span>My Numbers</span>
            </a>
        </li>
    </ul>

    <div class="nav-section-label">Integration</div>
    <ul class="nav-list">
        <li class="nav-item">
            <a href="/user/api.php" class="nav-link <?= $active_nav === 'api' ? 'active' : '' ?>">
                <span class="nav-link-icon">🔗</span>
                <span>API Settings</span>
            </a>
        </li>
    </ul>

    <div class="nav-section-label">Finance &amp; Profile</div>
    <ul class="nav-list">
        <li class="nav-item">
            <a href="/user/payouts.php" class="nav-link <?= $active_nav === 'payouts' ? 'active' : '' ?>">
                <span class="nav-link-icon">💸</span>
                <span>Payouts</span>
            </a>
        </li>
        <li class="nav-item">
            <a href="/user/notifications.php" class="nav-link <?= $active_nav === 'notifications' ? 'active' : '' ?>">
                <span class="nav-link-icon">🔔</span>
                <span>Notifications</span>
            </a>
        </li>
        <li class="nav-item">
            <a href="/user/profile.php" class="nav-link <?= $active_nav === 'profile' ? 'active' : '' ?>">
                <span class="nav-link-icon">👤</span>
                <span>Profile</span>
            </a>
        </li>
        <li class="nav-item">
            <a href="/user/logout.php" class="nav-link">
                <span class="nav-link-icon">⏏️</span>
                <span>Logout</span>
            </a>
        </li>
    </ul>
</aside>