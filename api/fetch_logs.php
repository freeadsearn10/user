<?php
/**
 * CRON / background script to fetch logs from all active API sources.
 *
 * Run via CLI or HTTP (recommended with master key):
 *   php api/fetch_logs.php
 *   or
 *   https://your-domain.com/api/fetch_logs.php?key=MASTER_KEY
 */

require_once __DIR__ . '/../config/config.php';

global $pdo;

// Optional master key protection
$masterKey = get_setting('api_master_key', '');
if (PHP_SAPI !== 'cli') {
    $provided = $_GET['key'] ?? '';
    if ($masterKey !== '' && !hash_equals($masterKey, $provided)) {
        http_response_code(403);
        echo 'Invalid master key';
        exit;
    }
}

$stmt = $pdo->query("SELECT * FROM api_sources WHERE status = 'on'");
$sources = $stmt->fetchAll();

if (!$sources) {
    if (PHP_SAPI !== 'cli') {
        echo "No active API sources.\n";
    }
    return;
}

// Prepared statements
$stmtCheck = $pdo->prepare(
    "SELECT id FROM sms_logs WHERE provider_log_id = :pid AND api_source_id = :src LIMIT 1"
);

$stmtMatch = $pdo->prepare("
    SELECT an.user_id,
           av.number,
           av.otp_rate AS number_rate,
           rt.otp_rate AS route_rate
    FROM assigned_numbers an
    JOIN available_numbers av ON an.number_id = av.id
    LEFT JOIN routes rt ON av.route_id = rt.id
    WHERE av.number = :number
    LIMIT 1
");

$stmtInsertLog = $pdo->prepare("
    INSERT INTO sms_logs
        (provider_log_id, api_source_id, user_id, number, country, `range`, sid,
         message, carrier, log_time, payout, status, created_at)
    VALUES
        (:provider_log_id, :api_source_id, :user_id, :number, :country, :range, :sid,
         :message, :carrier, :log_time, :payout, :status, NOW())
");

$stmtUpdateUser = $pdo->prepare("
    UPDATE users
    SET balance = balance + :amount,
        total_earned = total_earned + :amount
    WHERE id = :user_id
");

$stmtNotif = $pdo->prepare("
    INSERT INTO notifications (user_id, title, message, type, is_read, created_at)
    VALUES (:user_id, :title, :message, 'success', 0, NOW())
");

$stmtApiLog = $pdo->prepare("
    INSERT INTO api_logs (api_source_id, http_status, success, response_time_ms, error_message, raw_response)
    VALUES (:api_source_id, :http_status, :success, :response_time_ms, :error_message, :raw_response)
");

foreach ($sources as $src) {
    $sourceId = (int)$src['id'];
    $url = $src['url'];

    $start = microtime(true);
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 15,
        CURLOPT_FOLLOWLOCATION => true,
    ]);
    $body = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    curl_close($ch);
    $durationMs = (int)round((microtime(true) - $start) * 1000);

    $success = 0;
    $errorMessage = null;

    if ($body === false || $httpCode !== 200) {
        $errorMessage = $error ?: ('HTTP status ' . $httpCode);
    } else {
        $data = json_decode($body, true);
        if (is_array($data) && isset($data['data']['logs']) && is_array($data['data']['logs'])) {
            $success = 1;
            $logs = $data['data']['logs'];

            foreach ($logs as $log) {
                if (!is_array($log) || !isset($log['id'], $log['number'])) {
                    continue;
                }

                $providerId = (int)$log['id'];

                // Prevent duplicates
                $stmtCheck->execute([
                    ':pid' => $providerId,
                    ':src' => $sourceId,
                ]);
                if ($stmtCheck->fetch()) {
                    continue;
                }

                $number = (string)$log['number'];
                $country = $log['country'] ?? null;
                $range = $log['range'] ?? null;
                $sid = $log['app_name'] ?? null;
                $message = $log['sms'] ?? null;
                $carrier = $log['carrier'] ?? null;
                $timeStr = $log['time'] ?? null;

                $logDateTime = null;
                if ($timeStr) {
                    $today = new DateTime('now');
                    $logDateTime = $today->format('Y-m-d') . ' ' . $timeStr;
                }

                $userId = null;
                $payout = 0.0;
                $status = 'unmatched';

                // Match number against assigned numbers
                $stmtMatch->execute([':number' => $number]);
                if ($match = $stmtMatch->fetch()) {
                    $userId = (int)$match['user_id'];
                    $rate = (float)$match['number_rate'];
                    if ($rate <= 0 && $match['route_rate'] !== null) {
                        $rate = (float)$match['route_rate'];
                    }
                    $payout = $rate;
                    $status = 'delivered';
                }

                // Insert CDR
                $stmtInsertLog->execute([
                    ':provider_log_id' => $providerId,
                    ':api_source_id'   => $sourceId,
                    ':user_id'         => $userId,
                    ':number'          => $number,
                    ':country'         => $country,
                    ':range'           => $range,
                    ':sid'             => $sid,
                    ':message'         => $message,
                    ':carrier'         => $carrier,
                    ':log_time'        => $logDateTime,
                    ':payout'          => $payout,
                    ':status'          => $status,
                ]);

                if ($userId && $payout > 0) {
                    $stmtUpdateUser->execute([
                        ':amount'  => $payout,
                        ':user_id' => $userId,
                    ]);

                    $msg = sprintf(
                        'New OTP from %s (%s) on %s. Payout: $%s',
                        $sid ?? 'Unknown',
                        $carrier ?? 'Unknown carrier',
                        $number,
                        number_format($payout, 4, '.', '')
                    );
                    $stmtNotif->execute([
                        ':user_id' => $userId,
                        ':title'   => 'New OTP received',
                        ':message' => $msg,
                    ]);
                }
            }
        } else {
            $errorMessage = 'Invalid JSON structure or missing data.logs';
        }
    }

    // Insert API log
    $stmtApiLog->execute([
        ':api_source_id'    => $sourceId,
        ':http_status'      => $httpCode,
        ':success'          => $success,
        ':response_time_ms' => $durationMs,
        ':error_message'    => $errorMessage,
        ':raw_response'     => $body,
    ]);

    // Update last_polled_at
    $pdo->prepare("UPDATE api_sources SET last_polled_at = NOW() WHERE id = ?")
        ->execute([$sourceId]);

    if (PHP_SAPI !== 'cli') {
        echo sprintf(
            "Source %d (%s): HTTP %d, success=%d, %d ms\n",
            $sourceId,
            $url,
            $httpCode,
            $success,
            $durationMs
        );
    }
}