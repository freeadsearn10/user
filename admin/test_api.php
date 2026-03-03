<?php
require_once __DIR__ . '/../config/config.php';
require_admin();

header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['success' => false, 'message' => 'Invalid method']);
    exit;
}

$url = trim($_POST['url'] ?? '');
if (!filter_var($url, FILTER_VALIDATE_URL)) {
    echo json_encode(['success' => false, 'message' => 'Invalid API URL']);
    exit;
}

$ch = curl_init($url);
curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT => 10,
    CURLOPT_FOLLOWLOCATION => true,
]);
$body = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$error = curl_error($ch);
curl_close($ch);

if ($body === false || $httpCode !== 200) {
    echo json_encode([
        'success' => false,
        'message' => 'HTTP error while calling API: ' . ($error ?: ('Status ' . $httpCode)),
    ]);
    exit;
}

$data = json_decode($body, true);
if (!is_array($data) || !isset($data['data']['logs']) || !is_array($data['data']['logs'])) {
    echo json_encode([
        'success' => false,
        'message' => 'Invalid JSON structure. "data.logs" array not found.',
    ]);
    exit;
}

$logs = $data['data']['logs'];
$sample = $logs[0] ?? null;
$requiredFields = ['id','time','carrier','app_name','sms','number','range','country'];
$missing = [];
if ($sample) {
    foreach ($requiredFields as $field) {
        if (!array_key_exists($field, $sample)) {
            $missing[] = $field;
        }
    }
}

if ($missing) {
    echo json_encode([
        'success' => false,
        'message' => 'JSON structure missing required fields: ' . implode(', ', $missing),
        'sample'  => $sample,
    ]);
    exit;
}

echo json_encode([
    'success' => true,
    'message' => 'API setup successful. Structure is valid.',
    'sample'  => $sample,
]);