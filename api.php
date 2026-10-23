<?php
/**
 * api.php
 * -------
 * SMMM Mükellef Aylık Evrak Teslim PHP Uç Noktası (cPanel / Apache / Nginx uyumlu).
 * Verileri 'muhasebe_evraklar.json', 'muhasebe_reminders.json' ve 'webhook_settings.json' dosyalarında saklar.
 * e-Fatura / e-Arşiv UBL-TR XML ayrıştırma ve WhatsApp/SMS Webhook hatırlatma desteğine sahiptir.
 */

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

$dataFile = __DIR__ . '/muhasebe_evraklar.json';
$remindersFile = __DIR__ . '/muhasebe_reminders.json';
$settingsFile = __DIR__ . '/webhook_settings.json';

if (!file_exists($dataFile)) {
    file_put_contents($dataFile, json_encode([], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
}
if (!file_exists($remindersFile)) {
    file_put_contents($remindersFile, json_encode([], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
}
if (!file_exists($settingsFile)) {
    file_put_contents($settingsFile, json_encode([
        'provider' => 'whatsapp_cloud',
        'webhook_url' => '',
        'auth_token' => '',
        'template_message' => "Sayın {mukellef} yetkilisi, {donem} dönemi KDV/Muhtasar evraklarınızı lütfen sisteme yükleyiniz.",
        'is_active' => 1
    ], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
}

$action = $_GET['action'] ?? '';

// GET Talepleri
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    if ($action === 'reminder_logs') {
        echo file_get_contents($remindersFile) ?: '[]';
        exit;
    }
    if ($action === 'webhook_settings') {
        echo file_get_contents($settingsFile) ?: '{}';
        exit;
    }
    // Varsayılan: Evrak listesi
    $content = file_get_contents($dataFile);
    echo $content ?: '[]';
    exit;
}

// POST Talepleri
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $rawInput = file_get_contents('php://input');
    $input = json_decode($rawInput, true) ?: [];

    // 1. e-Fatura XML / ZIP Ayrıştırma
    if ($action === 'parse_efatura') {
        $content = $input['content'] ?? '';
        $filename = $input['filename'] ?? 'fatura.xml';
        $isBase64 = $input['is_base64'] ?? false;

        $xmlString = $content;
        if ($isBase64 || strpos($content, 'data:') === 0) {
            if (strpos($content, ',') !== false) {
                $content = explode(',', $content)[1];
            }
            $xmlString = base64_decode($content);
        }

        $invoices = [];
        // Basit XML parse denemesi
        try {
            // Namespace temizleme regex
            $cleanXml = preg_replace('/(<\/|<)[a-zA-Z0-9]+:([a-zA-Z0-9]+[ =>])/', '$1$2', $xmlString);
            $xml = @simplexml_load_string($cleanXml);
            if ($xml) {
                $faturaNo = (string)($xml->ID ?? 'GIB-2026-UNKNOWN');
                $tarih = (string)($xml->IssueDate ?? date('Y-m-d'));
                $satici = (string)($xml->AccountingSupplierParty->Party->PartyName->Name ?? 'Tedarikçi Firma');
                $saticiVkn = (string)($xml->AccountingSupplierParty->Party->PartyIdentification->ID ?? '');
                $alici = (string)($xml->AccountingCustomerParty->Party->PartyName->Name ?? 'Müşteri Firma');
                $matrah = floatval((string)($xml->TaxExclusiveAmount ?? $xml->LineExtensionAmount ?? 0));
                $kdv = floatval((string)($xml->TaxTotal->TaxAmount ?? 0));
                $odenecek = floatval((string)($xml->PayableAmount ?? ($matrah + $kdv)));

                $invoices[] = [
                    'belge_turu' => 'e-Fatura',
                    'fatura_no' => $faturaNo,
                    'tarih' => $tarih,
                    'fatura_tipi' => (string)($xml->InvoiceTypeCode ?? 'SATIS'),
                    'para_birimi' => (string)($xml->DocumentCurrencyCode ?? 'TRY'),
                    'satici_unvan' => $satici,
                    'satici_vkn' => $saticiVkn,
                    'alici_unvan' => $alici,
                    'matrah' => $matrah,
                    'kdv_tutar' => $kdv,
                    'odenecek_tutar' => $odenecek,
                    'dosya_adi' => $filename
                ];
            }
        } catch (\Exception $e) {}

        $totalMatrah = array_sum(array_column($invoices, 'matrah'));
        $totalKdv = array_sum(array_column($invoices, 'kdv_tutar'));
        $totalPayable = array_sum(array_column($invoices, 'odenecek_tutar'));

        echo json_encode([
            'success' => true,
            'invoices' => $invoices,
            'summary' => [
                'count' => count($invoices),
                'total_matrah' => round($totalMatrah, 2),
                'total_kdv' => round($totalKdv, 2),
                'total_payable' => round($totalPayable, 2),
                'currency' => 'TRY'
            ]
        ], JSON_UNESCAPED_UNICODE);
        exit;
    }

    // 2. Durum Güncelleme
    if ($action === 'update_status') {
        $receiptNo = $input['receipt_no'] ?? '';
        $newStatus = $input['status'] ?? 'İnceleniyor';
        $currentData = json_decode(file_get_contents($dataFile), true) ?: [];

        foreach ($currentData as &$item) {
            if ($item['receipt_no'] === $receiptNo) {
                $item['status'] = $newStatus;
                break;
            }
        }
        file_put_contents($dataFile, json_encode($currentData, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
        echo json_encode(['success' => true, 'status' => $newStatus]);
        exit;
    }

    // 3. Webhook Ayarları Güncelleme
    if ($action === 'webhook_settings') {
        $settings = [
            'provider' => $input['provider'] ?? 'whatsapp_cloud',
            'webhook_url' => trim($input['webhook_url'] ?? ''),
            'auth_token' => trim($input['auth_token'] ?? ''),
            'template_message' => trim($input['template_message'] ?? ''),
            'is_active' => 1
        ];
        file_put_contents($settingsFile, json_encode($settings, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
        echo json_encode(['success' => true, 'message' => 'Ayarlar güncellendi.']);
        exit;
    }

    // 4. Toplu Hatırlatma Gönderimi
    if ($action === 'toplu_hatirlatma') {
        $currentData = json_decode(file_get_contents($dataFile), true) ?: [];
        $settings = json_decode(file_get_contents($settingsFile), true) ?: [];
        $targetStatus = $input['target_status'] ?? [];
        $period = $input['period'] ?? 'Mart 2026';
        $template = $input['template_message'] ?? ($settings['template_message'] ?? '');
        $webhookUrl = trim($input['webhook_url'] ?? ($settings['webhook_url'] ?? ''));

        $logs = json_decode(file_get_contents($remindersFile), true) ?: [];
        $dispatched = [];

        foreach ($currentData as $item) {
            if (empty($targetStatus) || in_array($item['status'], $targetStatus)) {
                $msg = str_replace(
                    ['{mukellef}', '{donem}', '{ref_no}', '{vkn}'],
                    [$item['company_name'], $period, $item['receipt_no'], $item['vkn']],
                    $template
                );

                $status = 'SIMULATED_SUCCESS';
                if (!empty($webhookUrl)) {
                    $payload = json_encode([
                        'to' => $item['phone'],
                        'recipient' => $item['company_name'],
                        'message' => $msg,
                        'period' => $period,
                        'receipt_no' => $item['receipt_no']
                    ]);
                    $opts = [
                        'http' => [
                            'method'  => 'POST',
                            'header'  => "Content-Type: application/json\r\n",
                            'content' => $payload,
                            'timeout' => 5
                        ]
                    ];
                    $ctx = stream_context_create($opts);
                    $res = @file_get_contents($webhookUrl, false, $ctx);
                    $status = ($res !== false) ? 'DELIVERED' : 'FAILED';
                }

                $logEntry = [
                    'receipt_no' => $item['receipt_no'],
                    'company_name' => $item['company_name'],
                    'phone' => $item['phone'],
                    'status' => $status,
                    'message' => $msg,
                    'created_at' => date('c')
                ];
                $logs[] = $logEntry;
                $dispatched[] = $logEntry;
            }
        }

        file_put_contents($remindersFile, json_encode($logs, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
        echo json_encode([
            'success' => true,
            'dispatched_count' => count($dispatched),
            'logs' => $dispatched
        ], JSON_UNESCAPED_UNICODE);
        exit;
    }

    // 5. Standart Evrak Teslimatı Kaydı
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
        'parsed_invoices' => $input['parsed_invoices'] ?? [],
        'total_matrah' => floatval($input['total_matrah'] ?? 0.0),
        'total_kdv' => floatval($input['total_kdv'] ?? 0.0),
        'total_payable' => floatval($input['total_payable'] ?? 0.0),
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
