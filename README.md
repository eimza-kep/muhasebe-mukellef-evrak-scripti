# 📊 SMMM Mükellef Aylık Evrak & e-Fatura Toplama Portalı

[![CI](https://github.com/eimza-kep/muhasebe-mukellef-evrak-scripti/actions/workflows/ci.yml/badge.svg)](https://github.com/eimza-kep/muhasebe-mukellef-evrak-scripti/actions/workflows/ci.yml)
[![Canlı Demo](https://img.shields.io/badge/Demo-Canl%C4%B1%20Test%20Et-brightgreen.svg)](https://eimza-kep.github.io/muhasebe-mukellef-evrak-scripti/)
[![Lisans: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Kurulum Süresi](https://img.shields.io/badge/Kurulum-1%20Dakika-brightgreen)](#)
[![Bağımlılık](https://img.shields.io/badge/ba%C4%9F%C4%B1ml%C4%B1l%C4%B1k-0%20(S%C4%B1f%C4%B1r)-blue)](#)
[![UBL-TR Standardı](https://img.shields.io/badge/G%C4%B0B%20UBL--TR-2.1%20Uyumlu-blueviolet)](#)

Serbest Muhasebeci Mali Müşavirler (SMMM) ve muhasebe ofisleri için her ay mükelleflerden fatura, Z-raporu, banka ekstresi, fiş ve **e-Fatura / e-Arşiv XML dosyalarını** toplama stresini ortadan kaldıran, **1 dakikada kurulabilen** dijital evrak teslim, otomatik KDV matrah hesaplama ve WhatsApp/SMS Webhook hatırlatma portalı.

---

## 🌟 Temel Özellikler

1. **Aylık Mükellef Evrak Kontrol Listesi (Checklist):**
   - 🧾 Alış Faturaları ve Akaryakıt / Gider Fişleri
   - 📈 Satış Faturaları / e-Arşiv / e-Fatura / e-SMM Raporları
   - 🎰 ÖKC / Yazar Kasa Aylık Kümülatif Z-Raporları
   - 🏦 Banka Hesap Ekstreleri (PDF veya Excel Dökümü)
   - 💳 POS Günlük Gün Sonu ve Komisyon Raporları
   - 🏠 İşyeri Kira Ödeme Banka Dekontları
   - 👥 Personel İşe Giriş/Çıkış ve Masraf Formları

2. **⚡ UBL-TR 2.1 e-Fatura & e-Arşiv XML/ZIP Otomatik Ayrıştırıcı (Issue #2 Çözümü):**
   - Mükelleflerin sürükleyip bıraktığı tekli veya toplu `.xml` ve `.zip` arşivlerindeki e-fatura/e-arşiv belgeleri anında taranır.
   - Fatura No (`ID`), Düzenleme Tarihi (`IssueDate`), Satıcı/Alıcı VKN & Unvanı, Matrah (`TaxExclusiveAmount`), KDV Tutarı (`TaxAmount`), KDV Oran Dağılımı (%1, %10, %20) ve Genel Toplam otomatik hesaplanıp listelenir.
   - İstemci tarafında çalışan saf JavaScript DOM ayrıştırıcısı sayesinde GitHub Pages ve statik hosting üzerinde de sıfır gecikmeyle çalışır.

3. **📢 WhatsApp & SMS Webhook Otomatik Toplu Hatırlatma Motoru (Issue #1 Çözümü):**
   - Her ayın 1-20'si arasında veya yasal beyanname günleri öncesinde evrak teslim etmeyen ya da "Eksik Evrak Var" durumundaki mükelleflere toplu bildirim gönderimi.
   - **WhatsApp Cloud API**, **Netgsm SMS**, **Twilio** veya **Özel Webhook** URL entegrasyonu.
   - Özelleştirilebilir dinamik şablon değişkenleri: `{mukellef}`, `{donem}`, `{vkn}`, `{ref_no}`, `{portal_url}`.
   - Gönderilen tüm bildirimlerin tarih ve teslim durumlarıyla birlikte SQLite veritabanına loglanması (`reminder_logs`).

4. **🗓️ Yasal Vergi ve Beyanname Takvimi Sayacı:**
   - KDV-1 & KDV-2 (Her ayın 28'i), Muhtasar & SGK Prim (Her ayın 26'sı), Geçici Vergi (17'si) yasal mevzuat uyarılarını mükellefe form üzerinde canlı hatırlatır.

5. **📑 Dijital Teslim Tutanağı ve Ref No:**
   - Evraklar teslim edildiğinde `TESLIM-2026-4921` formatında resmi teslim tutanağı üretilir.
   - Mükellef formun çıktısını PDF veya yazdırılabilir formatta anında alabilir.

6. **💻 Mali Müşavir Yönetim Paneli (`admin.html`):**
   - Mükellef teslim durumlarını anlık izleme (`İnceleniyor` ➔ `Eksik Evrak Var` ➔ `Muhasebeleştirildi`).
   - Mükelleflerin teslim ettiği e-Fatura matrah ve KDV dökümlerini tek tıkla inceleme.
   - Tek tıkla Excel/CSV dökümü alma (`smmm_mukellef_evraklari.csv`).

7. **🚀 Çift Arka Uç ve Sıfır Harici Bağımlılık (Zero-Dependency):**
   - **Python VPS / Yerel:** Python 3 standard kütüphanesi (`http.server`, `sqlite3`, `xml.etree`, `zipfile`).
   - **cPanel / Paylaşımlı Hosting:** `api.php` ve JSON dosya depolama.
   - **Statik Mod:** Tarayıcı yerel hafızası (`localStorage`).

---

## 🚀 Hızlı Kurulum & Çalıştırma Seçenekleri

### 1. Windows'ta Tek Tıkla Çalıştırma (En Kolay)
Klasördeki **`Baslat.bat`** dosyasına çift tıklayın! Yerel Python sunucusu otomatik başlar ve tarayıcınızda form açılır.

### 2. Linux & macOS Üzerinde Çalıştırma
```bash
chmod +x baslat.sh
./baslat.sh
```

### 3. Python Sunucusu ile Manuel Çalıştırma
```bash
python server.py
```
- Mükellef Evrak Portalı: `http://localhost:8083/index.html`
- Mali Müşavir Kontrol Paneli: `http://localhost:8083/admin.html`
- Servis Sağlık Durumu: `http://localhost:8083/health`

### 4. Docker ile Çalıştırma
```bash
docker build -t muhasebe-portal .
docker run -d -p 8083:8083 --name muhasebe-app muhasebe-portal
```

### 5. Paylaşımlı Hosting / cPanel (Apache & PHP)
1. Dosyaları zip olarak indirin.
2. Sitenizin `public_html/evrak` dizinine yükleyin.
3. `https://siteniz.com/evrak/` adresinden doğrudan kullanın! `api.php` arka planda SQLite gerektirmeden JSON tabanlı olarak tam uyumlu çalışır.

---

## 📡 REST API Referansı

| Metot | Uç Nokta | Açıklama |
|---|---|---|
| `GET` | `/health` | Servis sağlık kontrolü |
| `GET` | `/api/evrak-listesi` | Tüm mükellef evrak teslim kayıtlarını ve e-fatura özetlerini listeler |
| `POST` | `/api/evrak-teslim` | Yeni evrak teslim tutanağı ve e-fatura kalemlerini kaydeder |
| `POST` | `/api/update-status` | Evrak teslim durumunu günceller (`İnceleniyor`, `Eksik Evrak Var`, `Muhasebeleştirildi`) |
| `POST` | `/api/parse-efatura` | Base64 veya XML metnini ayrıştırarak fatura başlıklarını ve KDV matrahını döner |
| `POST` | `/api/toplu-hatirlatma` | Seçili durumdaki mükelleflere WhatsApp/SMS Webhook üzerinden toplu hatırlatma tetikler |
| `GET` | `/api/reminder-logs` | Gönderilen hatırlatmaların geçmişini ve durumlarını listeler |
| `GET` / `POST` | `/api/webhook-settings` | Webhook URL, API token ve şablon yapılandırmasını okur ve günceller |

### Örnek: e-Fatura XML / ZIP Ayrıştırma İsteği (`POST /api/parse-efatura`)
```json
{
  "filename": "faturalar.zip",
  "content": "<base64_encoded_zip_data>",
  "is_base64": true
}
```

**Yanıt:**
```json
{
  "success": true,
  "invoices": [
    {
      "fatura_no": "GIB2026000000042",
      "tarih": "2026-03-24",
      "satici_unvan": "Örnek Bilişim A.Ş.",
      "satici_vkn": "1234567890",
      "alici_unvan": "Anadolu Teknoloji Ltd.",
      "matrah": 120000.0,
      "kdv_tutar": 24000.0,
      "odenecek_tutar": 144000.0,
      "kdv_oranlari": [{"oran": 20.0, "tutar": 24000.0}]
    }
  ],
  "summary": {
    "count": 1,
    "total_matrah": 120000.0,
    "total_kdv": 24000.0,
    "total_payable": 144000.0,
    "currency": "TRY"
  }
}
```

---

## 💬 WhatsApp & SMS Webhook Entegrasyon Rehberi

Admin panelindeki **"⚙️ Webhook Ayarları"** menüsünden aşağıdaki sağlayıcıları kolayca bağlayabilirsiniz:

1. **WhatsApp Cloud API (Meta Graph API):**
   - Webhook URL: `https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages`
   - Authorization: Bearer Token
2. **Netgsm SMS API:**
   - Webhook URL: `https://api.netgsm.com.tr/sms/send/get`
3. **Özel Webhook:**
   - İstediğiniz Node.js, Python veya n8n / Zapier webhook adresini yazabilirsiniz.

---

## 🧪 Birim ve Entegrasyon Testleri

Tüm bileşenler sıfır harici kütüphane bağımlılığıyla Python `unittest` süiti üzerinden test edilebilir:

```bash
python scripts/test_muhasebe.py
```

Test Kapsamı:
- Veritabanı başlatma ve otomatik şema göçleri (`migrations`)
- Evrak teslimat akışı ve toplam tutarların kaydı
- GİB UBL-TR 2.1 XML şemasının ayrıştırılması
- ZIP arşivi içerisinden çoklu e-fatura çıkarımı ve KDV dökümü
- Webhook şablon değişkenlerinin yerleştirilmesi ve loglama
- Evrak durumu güncelleme yaşam döngüsü

---

## 🌐 E-Dönüşüm Açık Kaynak Ekosistemi

Bu script, [@eimza-kep](https://github.com/eimza-kep) açık kaynak ekosisteminin muhasebe ofisi iş akışı bileşenidir. İlgili diğer araçlar:

* 📊 [muhasebe-excel-sablonlari](https://github.com/eimza-kep/muhasebe-excel-sablonlari) - e-SMM, Tevkifat, Kıdem ve Bordro hesaplayıcıları.
* 📄 [e-fatura-xml-goruntuleyici](https://github.com/eimza-kep/e-fatura-xml-goruntuleyici) - Mükellef e-Fatura ve e-İrsaliye XML dosyalarını ayrıştırma ve KDV dökümü.
* 📑 [gib-edefter-berat-xml-dogrulayici](https://github.com/eimza-kep/gib-edefter-berat-xml-dogrulayici) - Aylık berat ve defter XML hash kontrolü.
* 📋 [smmm-stok-sayim-tutanak-scripti](https://github.com/eimza-kep/smmm-stok-sayim-tutanak-scripti) - Yıl sonu ve dönemlik fiili stok sayım tutanağı hazırlayıcı.
* 🌟 [awesome-turkiye-e-donusum](https://github.com/eimza-kep/awesome-turkiye-e-donusum) - Türkiye e-Dönüşüm açık kaynak araçları ve kütüphaneleri kürasyonu.

---

## 📜 Lisans

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır. Mali müşavirler, muhasebe büroları ve yazılım geliştiriciler tarafından ticari veya gayriticari olarak serbestçe kullanılabilir.
