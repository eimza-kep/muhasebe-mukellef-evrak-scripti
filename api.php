<?php
/**
 * api.php
 * -------
 * SMMM Mükellef Aylık Evrak Teslim PHP Uç Noktası (cPanel / Apache / Nginx uyumlu).
 * Verileri 'muhasebe_evraklar.json' dosyasında saklar.
 */

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

$dataFile = __DIR__ . '/muhasebe_evraklar.json';

if (!file_exists($dataFile)) {
    file_put_contents($dataFile, json_encode([], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
}

if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    $content = file_get_contents($dataFile);
    echo $content ?: '[]';
    exit;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $input = json_decode(file_get_contents('php://input'), true);
    if (!$input) {
        http_response_code(400);
        echo json_encode(['error' => 'Geçersiz veri.']);
        exit;
    }

    $currentData = json_decode(file_get_contents($dataFile), true) ?: [];
    $receiptNo = 'TESLIM-2026-' . rand(1000, 9999);

    $entry = [
        'id' => count($currentData) + 1,
        'receipt_no' => $receiptNo,
        'company_name' => htmlspecialchars($input['company_name'] ?? ''),
        'vkn' => htmlspecialchars($input['vkn'] ?? ''),
        'contact_name' => htmlspecialchars($input['contact_name'] ?? ''),
        'phone' => htmlspecialchars($input['phone'] ?? ''),
        'period' => htmlspecialchars($input['period'] ?? ''),
        'delivered_docs' => $input['delivered_docs'] ?? [],
        'notes' => htmlspecialchars($input['notes'] ?? ''),
        'files_count' => intval($input['files_count'] ?? 0),
        'status' => 'İnceleniyor',
        'created_at' => date('c')
    ];

    $currentData[] = $entry;
    file_put_contents($dataFile, json_encode($currentData, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));

    echo json_encode([
        'success' => true,
        'receipt_no' => $receiptNo,
        'message' => 'Evrak teslim bildiriminiz başarıyla kaydedildi.'
    ], JSON_UNESCAPED_UNICODE);
    exit;
}
?>
