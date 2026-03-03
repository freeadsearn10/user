<?php
/**
 * User-facing API to retrieve SMS logs in JSON form.
 *
 * GET /api/user_logs.php?api_key=XXX&limit=50&since_id=123
 */

require_once __DIR__ . '/../config/config.php';

header('Content-Type: application/json');

$apiKey = $_GET['api_key'] ?? '';
if ($apiKey === '') {
    echo json_encode(['success' => false, 'message' => 'Missing api_key']);
    exit;
}

global $pdo;
$stmt = $pdo->prepare("SELECT id FROM users WHERE api_key = :key AND status = 'active' LIMIT 1");
$stmt->execute([':key' => $apiKey]);
$user = $stmt->fetch();

if (!$user) {
    echo json_encode(['success' => false, 'message' => 'Invalid or inactive api_key']);
    exit;
}

$userId = (int)$user['id'];

$limit = isset($_GET['limit']) ? (int)$_GET['limit'] : 50;
if ($limit <= 0 || $limit > 200) {
    $limit = 50;
}

$sinceId = isset($_GET['since_id']) ? (int)$_GET['since_id'] : 0;

$where = "WHERE user_id = :uid";
$params = [':uid' => $userId];

if ($sinceId > 0) {
    $where .= " AND id > :since_id";
    $params[':since_id'] = $sinceId;
}

$sql = "
    SELECT id, created_at, log_time, sid, message, number, country, `range`, carrier, payout
    FROM sms_logs
    $where
    ORDER BY id DESC
    LIMIT $limit
";

$stmt = $pdo->prepare($sql);
$stmt->execute($params);
$rows = $stmt->fetchAll();

$data = [];
foreach ($rows as $row) {
    $time = $row['log_time'] ?: $row['created_at'];
    $timeOnly = substr($time, 11, 8);
    $data[] = [
        'id'         => (int)$row['id'],
        'created_at' => $row['created_at'],
        'time'       => $timeOnly,
        'sid'        => $row['sid'],
        'message'    => $row['message'],
        'number'     => $row['number'],
        'range'      => $row['range'],
        'country'    => $row['country'],
        'carrier'    => $row['carrier'],
        'payout'     => (float)$row['payout'],
    ];
}

echo json_encode(['success' => true, 'data' => $data]);