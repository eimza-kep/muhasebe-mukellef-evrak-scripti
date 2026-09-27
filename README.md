# 📊 SMMM Mükellef Aylık Evrak & Fiş Toplama Portalı

[![CI](https://github.com/eimza-kep/muhasebe-mukellef-evrak-scripti/actions/workflows/ci.yml/badge.svg)](https://github.com/eimza-kep/muhasebe-mukellef-evrak-scripti/actions/workflows/ci.yml)
[![Canlı Demo](https://img.shields.io/badge/Demo-Canl%C4%B1%20Test%20Et-brightgreen.svg)](https://eimza-kep.github.io/muhasebe-mukellef-evrak-scripti/)
[![Lisans: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Kurulum Süresi](https://img.shields.io/badge/Kurulum-1%20Dakika-brightgreen)](#)
[![Bağımlılık](https://img.shields.io/badge/ba%C4%9F%C4%B1ml%C4%B1l%C4%B1k-0%20(S%C4%B1f%C4%B1r)-blue)](#)

Serbest Muhasebeci Mali Müşavirler (SMMM) ve muhasebe ofisleri için her ay mükelleflerden fatura, Z-raporu, banka ekstresi ve fiş toplama stresini ortadan kaldıran, **1 dakikada kurulabilen** dijital evrak teslim ve denetim portalı.

---

## 🌟 Temel Özellikler

1. **Aylık Mükellef Evrak Kontrol Listesi (Checklist):**
   - Alış Faturaları ve Akaryakıt/Gider Fişleri
   - Satış Faturaları / e-Arşiv / e-SMM Raporları
   - ÖKC / Yazar Kasa Aylık Z-Raporları
   - Banka Hesap Ekstreleri (PDF/Excel)
   - POS Günlük Gün Sonu ve Komisyon Raporları
   - İşyeri Kira Ödeme Dekontları
   - Personel İşe Giriş/Çıkış ve Masraf Formları
2. **Dijital Teslim Tutanağı ve Ref No:**
   - Evraklar teslim edildiğinde `TESLIM-2026-4921` formatında resmi teslim tutanağı üretilir.
   - Mükellef formun çıktısını PDF veya yazdırılabilir formatta anında alabilir.
3. **Mali Müşavir Yönetim Paneli (`admin.html`):**
   - Hangi mükellefin evrak teslim ettiğini, kimlerin geciktiğini anlık takip etme.
   - Durum güncelleme (`İnceleniyor` -> `Eksik Evrak Var` -> `Muhasebeleştirildi`).
   - Tek tıkla Excel/CSV dökümü alma.
4. **Tek Tıkla WhatsApp Hatırlatma Entegrasyonu:**
   - Evrak göndermeyen mükellefe tek tıkla otomatik WhatsApp hatırlatma mesajı açar.
5. **Çift Arka Uç Desteği:**
   - **cPanel / Paylaşımlı Hosting:** `api.php` ve JSON depolama.
   - **VPS / Yerel:** Python `server.py` ve SQLite veritabanı.
   - **Statik:** Tarayıcı yerel hafızası (`localStorage`).

---

## 🚀 1 Dakikada Kurulum

### 1. Windows'ta Tek Tıkla Çalıştırma (Test & Demo)
Klasördeki **`Baslat.bat`** dosyasına çift tıklayın! Yerel sunucu otomatik başlar ve tarayıcınızda form açılır.

### 2. Paylaşımlı Hosting / cPanel (Apache & PHP)
1. Dosyaları zip olarak indirin.
2. Sitenizin `public_html/evrak` dizinine yükleyin.
3. `https://siteniz.com/evrak/` adresinden doğrudan kullanın!

### 3. Python Sunucusu ile Çalıştırma
```bash
python server.py
```
- Mükellef Evrak Teslim Portalı: `http://localhost:8083/index.html`
- Mali Müşavir Kontrol Paneli: `http://localhost:8083/admin.html`

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

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır. Mali müşavirler ve muhasebe büroları tarafından serbestçe kullanılabilir.

