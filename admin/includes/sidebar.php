<?php
$active_nav = $active_nav ?? '';
$user = current_user();
$system_name = get_setting('system_name', 'IPRN SMS Panel');
?>
<aside class="app-sidebar">
    <div class="brand">
        <div class="brand-logo">I</div>
        <div class="brand-text">
            <div class="brand-title"><?= htmlspecialchars($system_name) ?></div>
            <div class="brand-subtitle">Admin Panel</div>
        </div>
    </div>

    <div class="mb-3 small text-muted">
        Logged in as<br>
        <strong><?= htmlspecialchars($user['username'] ?? 'Admin') ?></strong>
    </div>

    <div class="nav-section-label">Overview</div>
    <ul class="nav-list">
        <li class="nav-item">
            <a href="/admin/dashboard.php" class="nav-link <?= $active_nav === 'dashboard' ? 'active' : '' ?>">
                <span class="nav-link-icon">📊</span>
                <span>Dashboard</span>
            </a>
        </li>
    </ul>

    <div class="nav-section-label">Traffic &amp; Routes</div>
    <ul class="nav-list">
        <li class="nav-item">
            <a href="/admin/api_sources.php" class="nav-link <?= $active_nav === 'api_sources' ? 'active' : '' ?>">
                <span class="nav-link-icon">🌐</span>
                <span>API Sources</span>
            </a>
        </li>
        <li class="nav-item">
            <a href="/admin/routes.php" class="nav-link <?= $active_nav === 'routes' ? 'active' : '' ?>">
                <span class="nav-link-icon">🛰️</span>
                <span>Routes / Ranges</span>
            </a>
        </li>
        <li class="nav-item">
            <a href="/admin/numbers.php" class="nav-link <?= $active_nav === 'numbers' ? 'active' : '' ?>">
                <span class="nav-link-icon">🔢</span>
                <span>Number Pool</span>
            </a>
        </li>
        <li class="nav-item">
            <a href="/admin/assign_numbers.php" class="nav-link <?= $active_nav === 'assign_numbers' ? 'active' : '' ?>">
                <span class="nav-link-icon">🎯</span>
                <span>Assign Numbers</span>
            </a>
        </li>
    </ul>

    <div class="nav-section-label">Users &amp; Finance</div>
    <ul class="nav-list">
        <li class="nav-item">
            <a href="/admin/users.php" class="nav-link <?= $active_nav === 'users' ? 'active' : '' ?>">
                <span class="nav-link-icon">👥</span>
                <span>Users</span>
            </a>
        </li>
        <li class="nav-item">
            <a href="/admin/sms_logs.php" class="nav-link <?= $active_nav === 'sms_logs' ? 'active' : '' ?>">
                <span class="nav-link-icon">📩</span>
                <span>SMS Logs (CDR)</span>
            </a>
        </li>
        <li class="nav-item">
            <a href="/admin/payouts.php" class="nav-link <?= $active_nav === 'payouts' ? 'active' : '' ?>">
                <span class="nav-link-icon">💸</span>
                <span>Payouts</span>
            </a>
        </li>
    </ul>

    <div class="nav-section-label">System</div>
    <ul class="nav-list">
        <li class="nav-item">
            <a href="/admin/settings.php" class="nav-link <?= $active_nav === 'settings' ? 'active' : '' ?>">
                <span class="nav-link-icon">⚙️</span>
                <span>Settings</span>
            </a>
        </li>
        <li class="nav-item">
            <a href="/admin/logout.php" class="nav-link">
                <span class="nav-link-icon">⏏️</span>
                <span>Logout</span>
            </a>
        </li>
    </ul>
</aside>