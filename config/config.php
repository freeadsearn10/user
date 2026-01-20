<?php
if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

require_once __DIR__ . '/db.php';

/**
 * Basic URL helper
 */
function redirect(string $path): void
{
    header('Location: ' . $path);
    exit;
}

/**
 * Flash messages
 */
function flash(string $type, string $message): void
{
    $_SESSION['flash'][$type][] = $message;
}

function get_flashes(): array
{
    $flashes = $_SESSION['flash'] ?? [];
    unset($_SESSION['flash']);
    return $flashes;
}

/**
 * CSRF protection
 */
function csrf_token(): string
{
    if (empty($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['csrf_token'];
}

function verify_csrf(): void
{
    if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
        return;
    }
    $token = $_POST['csrf_token'] ?? '';
    if (!isset($_SESSION['csrf_token']) || !hash_equals($_SESSION['csrf_token'], $token)) {
        http_response_code(400);
        echo 'Invalid CSRF token';
        exit;
    }
}

/**
 * Authentication helpers
 */
function current_user(): ?array
{
    if (empty($_SESSION['user_id'])) {
        return null;
    }
    static $user;
    if ($user === null) {
        global $pdo;
        $stmt = $pdo->prepare('SELECT * FROM users WHERE id = ? LIMIT 1');
        $stmt->execute([$_SESSION['user_id']]);
        $user = $stmt->fetch() ?: null;
    }
    return $user;
}

function require_login(): void
{
    if (empty($_SESSION['user_id'])) {
        redirect('/user/login.php');
    }
}

function require_admin(): void
{
    if (empty($_SESSION['user_id']) || ($_SESSION['role'] ?? '') !== 'admin') {
        redirect('/admin/login.php');
    }
}

function require_user(): void
{
    if (empty($_SESSION['user_id']) || ($_SESSION['role'] ?? '') !== 'user') {
        redirect('/user/login.php');
    }
}

/**
 * API key generator
 */
function generate_api_key(): string
{
    return bin2hex(random_bytes(32));
}

/**
 * Settings helpers
 */
function get_setting(string $name, $default = null)
{
    static $settings = null;
    if ($settings === null) {
        global $pdo;
        $settings = [];
        try {
            $stmt = $pdo->query('SELECT name, value FROM settings');
            foreach ($stmt as $row) {
                $settings[$row['name']] = $row['value'];
            }
        } catch (Throwable $e) {
            $settings = [];
        }
    }
    return $settings[$name] ?? $default;
}

function set_setting(string $name, string $value): void
{
    global $pdo;
    $stmt = $pdo->prepare('INSERT INTO settings (name, value) VALUES (:name, :value)
        ON DUPLICATE KEY UPDATE value = VALUES(value)');
    $stmt->execute([
        ':name'  => $name,
        ':value' => $value,
    ]);
}

/**
 * Simple helper to format money
 */
function fmt_amount($amount): string
{
    return number_format((float)$amount, 4, '.', ',');
}