# -*- coding: utf-8 -*-
"""
server.py
---------
SMMM Mükellef Aylık Evrak Toplama Portalı - Sıfır Bağımlılıklı Python Sunucusu.
Gelir İdaresi Başkanlığı UBL-TR e-Fatura & e-Arşiv XML/ZIP ayrıştırıcı ve
WhatsApp / SMS Webhook otomatik hatırlatma motorunu içerir.
"""

import os
import sys
import json
import sqlite3
import random
import re
import io
import base64
import zipfile
import urllib.request
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PORT = int(os.environ.get("PORT", 8083))
DB_FILE = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "muhasebe_evraklar.db"))

def init_db():
    """Veritabanını ve gerekli tabloları başlatır/günceller."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_no TEXT UNIQUE,
                company_name TEXT,
                vkn TEXT,
                contact_name TEXT,
                phone TEXT,
                period TEXT,
                delivered_docs TEXT,
                notes TEXT,
                files_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'İnceleniyor',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                parsed_invoices TEXT,
                total_matrah REAL DEFAULT 0.0,
                total_kdv REAL DEFAULT 0.0,
                total_payable REAL DEFAULT 0.0
            )
        """)

        # Mevcut veritabanlarında eksik sütunları güvenli şekilde ekleme (migrations)
        cursor.execute("PRAGMA table_info(submissions)")
        columns = [row[1] for row in cursor.fetchall()]
        if "parsed_invoices" not in columns:
            cursor.execute("ALTER TABLE submissions ADD COLUMN parsed_invoices TEXT")
        if "total_matrah" not in columns:
            cursor.execute("ALTER TABLE submissions ADD COLUMN total_matrah REAL DEFAULT 0.0")
        if "total_kdv" not in columns:
            cursor.execute("ALTER TABLE submissions ADD COLUMN total_kdv REAL DEFAULT 0.0")
        if "total_payable" not in columns:
            cursor.execute("ALTER TABLE submissions ADD COLUMN total_payable REAL DEFAULT 0.0")

        # Hatırlatma kayıtları tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminder_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_no TEXT,
                company_name TEXT,
                phone TEXT,
                channel TEXT DEFAULT 'whatsapp',
                status TEXT DEFAULT 'SENT',
                message TEXT,
                webhook_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Webhook ayarları tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS webhook_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT DEFAULT 'whatsapp_cloud',
                webhook_url TEXT,
                auth_token TEXT,
                template_message TEXT,
                is_active INTEGER DEFAULT 1,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def clean_tag(tag):
    """XML etiketindeki XML namespace bilgisini temizler."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag

def parse_ubl_xml_content(xml_text):
    """
    UBL-TR e-Fatura veya e-Arşiv XML metnini ayrıştırır.
    Fatura numarası, tarih, satıcı/alıcı VKN-Unvan, matrah, KDV ve ödenecek tutarı çeker.
    """
    try:
        root = ET.fromstring(xml_text)
    except Exception as e:
        return None

    root_tag = clean_tag(root.tag)
    is_despatch = "DespatchAdvice" in root_tag
    belge_turu = "e-İrsaliye" if is_despatch else "e-Fatura"

    invoice = {
        "belge_turu": belge_turu,
        "fatura_no": "",
        "uuid": "",
        "tarih": "",
        "fatura_tipi": "SEVK" if is_despatch else "SATIS",
        "para_birimi": "TRY",
        "satici_unvan": "",
        "satici_vkn": "",
        "alici_unvan": "",
        "alici_vkn": "",
        "matrah": 0.0,
        "kdv_tutar": 0.0,
        "odenecek_tutar": 0.0,
        "kdv_oranlari": []
    }

    # Meta veriler
    for elem in root.iter():
        tag = clean_tag(elem.tag)
        val = (elem.text or "").strip()
        if tag == "ID" and not invoice["fatura_no"]:
            invoice["fatura_no"] = val
        elif tag == "UUID" and not invoice["uuid"]:
            invoice["uuid"] = val
        elif tag == "IssueDate" and not invoice["tarih"]:
            invoice["tarih"] = val
        elif tag == "InvoiceTypeCode" and not is_despatch:
            invoice["fatura_tipi"] = val
        elif tag == "DocumentCurrencyCode" and not invoice["para_birimi"]:
            invoice["para_birimi"] = val

    # Satıcı bilgisi
    for party in root.iter():
        if clean_tag(party.tag) in {"AccountingSupplierParty", "DespatchSupplierParty"}:
            for child in party.iter():
                ctag = clean_tag(child.tag)
                cval = (child.text or "").strip()
                if ctag in ["RegistrationName", "Name"] and not invoice["satici_unvan"]:
                    invoice["satici_unvan"] = cval
                elif ctag == "ID" and not invoice["satici_vkn"]:
                    invoice["satici_vkn"] = cval

    # Alıcı bilgisi
    for party in root.iter():
        if clean_tag(party.tag) in {"AccountingCustomerParty", "DeliveryCustomerParty"}:
            for child in party.iter():
                ctag = clean_tag(child.tag)
                cval = (child.text or "").strip()
                if ctag in ["RegistrationName", "Name"] and not invoice["alici_unvan"]:
                    invoice["alici_unvan"] = cval
                elif ctag == "ID" and not invoice["alici_vkn"]:
                    invoice["alici_vkn"] = cval

    # Tutarlar
    for elem in root.iter():
        tag = clean_tag(elem.tag)
        val = (elem.text or "0").replace(",", ".").strip()
        try:
            val_float = float(val)
            if tag in ["LineExtensionAmount", "TaxExclusiveAmount"] and invoice["matrah"] == 0:
                invoice["matrah"] = val_float
            elif tag == "TaxAmount" and invoice["kdv_tutar"] == 0:
                invoice["kdv_tutar"] = val_float
            elif tag == "PayableAmount" and invoice["odenecek_tutar"] == 0:
                invoice["odenecek_tutar"] = val_float
        except ValueError:
            pass

    # KDV Oranları ve Detayları
    for sub in root.iter():
        if clean_tag(sub.tag) == "TaxSubtotal":
            sub_kdv = 0.0
            sub_oran = 0.0
            for sc in sub.iter():
                sctag = clean_tag(sc.tag)
                scval = (sc.text or "0").replace(",", ".").strip()
                if sctag == "TaxAmount":
                    try: sub_kdv = float(scval)
                    except: pass
                elif sctag == "Percent":
                    try: sub_oran = float(scval)
                    except: pass
            if sub_oran > 0 or sub_kdv > 0:
                invoice["kdv_oranlari"].append({"oran": sub_oran, "tutar": sub_kdv})

    # Eğer matrah sıfır ama ödenecek tutar ve KDV varsa matrahı türet
    if invoice["matrah"] == 0 and invoice["odenecek_tutar"] > 0:
        invoice["matrah"] = max(0.0, round(invoice["odenecek_tutar"] - invoice["kdv_tutar"], 2))
    elif invoice["odenecek_tutar"] == 0 and (invoice["matrah"] > 0 or invoice["kdv_tutar"] > 0):
        invoice["odenecek_tutar"] = round(invoice["matrah"] + invoice["kdv_tutar"], 2)

    return invoice

def parse_efatura_files(file_bytes, filename=""):
    """
    Tek bir XML veya içinde birden çok XML barındıran ZIP dosyasını ayrıştırır.
    """
    invoices = []
    fname_lower = (filename or "").lower()

    if fname_lower.endswith(".zip") or file_bytes[:4] == b"PK\x03\x04":
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                for member in zf.namelist():
                    if member.lower().endswith(".xml") and not member.startswith("__MACOSX"):
                        try:
                            content = zf.read(member).decode("utf-8", errors="replace")
                            inv = parse_ubl_xml_content(content)
                            if inv:
                                inv["dosya_adi"] = os.path.basename(member)
                                invoices.append(inv)
                        except Exception:
                            continue
        except Exception as e:
            pass
    else:
        # Doğrudan XML
        try:
            content = file_bytes.decode("utf-8", errors="replace")
            inv = parse_ubl_xml_content(content)
            if inv:
                inv["dosya_adi"] = os.path.basename(filename) if filename else "fatura.xml"
                invoices.append(inv)
        except Exception:
            pass

    total_matrah = round(sum(inv["matrah"] for inv in invoices), 2)
    total_kdv = round(sum(inv["kdv_tutar"] for inv in invoices), 2)
    total_payable = round(sum(inv["odenecek_tutar"] for inv in invoices), 2)

    return {
        "success": True,
        "invoices": invoices,
        "summary": {
            "count": len(invoices),
            "total_matrah": total_matrah,
            "total_kdv": total_kdv,
            "total_payable": total_payable,
            "currency": invoices[0]["para_birimi"] if invoices else "TRY"
        }
    }

class EvrakHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy", "service": "muhasebe-evrak"}).encode("utf-8"))
            return

        if parsed.path == "/api/evrak-listesi":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()

            with sqlite3.connect(DB_FILE) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM submissions ORDER BY created_at DESC")
                rows = [dict(r) for r in cursor.fetchall()]
                for r in rows:
                    if r.get("delivered_docs"):
                        try:
                            r["delivered_docs"] = json.loads(r["delivered_docs"])
                        except Exception:
                            pass
                    if r.get("parsed_invoices"):
                        try:
                            r["parsed_invoices"] = json.loads(r["parsed_invoices"])
                        except Exception:
                            r["parsed_invoices"] = []
                self.wfile.write(json.dumps(rows, ensure_ascii=False).encode("utf-8"))
            return

        if parsed.path == "/api/reminder-logs":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()

            with sqlite3.connect(DB_FILE) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM reminder_logs ORDER BY created_at DESC LIMIT 100")
                rows = [dict(r) for r in cursor.fetchall()]
                self.wfile.write(json.dumps(rows, ensure_ascii=False).encode("utf-8"))
            return

        if parsed.path == "/api/webhook-settings":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()

            with sqlite3.connect(DB_FILE) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM webhook_settings ORDER BY id DESC LIMIT 1")
                row = cursor.fetchone()
                settings = dict(row) if row else {
                    "provider": "whatsapp_cloud",
                    "webhook_url": "",
                    "auth_token": "",
                    "template_message": "Sayın {mukellef} yetkilisi, {donem} dönemi KDV/Muhtasar beyanname hazırlıkları için muhasebe evraklarınızı en geç ayın 20'sine kadar portalımıza yükleyiniz: {portal_url}",
                    "is_active": 1
                }
                self.wfile.write(json.dumps(settings, ensure_ascii=False).encode("utf-8"))
            return

        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8", errors="replace") if content_length > 0 else "{}"
        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if parsed.path == "/api/evrak-teslim":
            receipt_no = f"TESLIM-2026-{random.randint(1000, 9999)}"
            docs_json = json.dumps(data.get("delivered_docs", []), ensure_ascii=False)
            invoices_json = json.dumps(data.get("parsed_invoices", []), ensure_ascii=False)

            total_matrah = float(data.get("total_matrah", 0.0))
            total_kdv = float(data.get("total_kdv", 0.0))
            total_payable = float(data.get("total_payable", 0.0))

            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO submissions (
                        receipt_no, company_name, vkn, contact_name, phone,
                        period, delivered_docs, notes, files_count,
                        parsed_invoices, total_matrah, total_kdv, total_payable
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    receipt_no,
                    data.get("company_name", ""),
                    data.get("vkn", ""),
                    data.get("contact_name", ""),
                    data.get("phone", ""),
                    data.get("period", ""),
                    docs_json,
                    data.get("notes", ""),
                    int(data.get("files_count", 0)),
                    invoices_json,
                    total_matrah,
                    total_kdv,
                    total_payable
                ))
                conn.commit()

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            resp = {
                "success": True,
                "receipt_no": receipt_no,
                "message": "Aylık evrak teslim bildiriminiz ve e-fatura dökümünüz başarıyla kaydedilmiştir."
            }
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode("utf-8"))
            return

        elif parsed.path == "/api/parse-efatura":
            filename = data.get("filename", "fatura.xml")
            content_str = data.get("content", "")
            is_base64 = data.get("is_base64", False)

            if is_base64 or filename.lower().endswith(".zip") or content_str.startswith("data:"):
                # Data URL prefixini temizle
                if "," in content_str:
                    content_str = content_str.split(",", 1)[1]
                try:
                    raw_bytes = base64.b64decode(content_str)
                except Exception:
                    raw_bytes = content_str.encode("utf-8")
            else:
                raw_bytes = content_str.encode("utf-8")

            result = parse_efatura_files(raw_bytes, filename)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
            return

        elif parsed.path == "/api/update-status":
            receipt_no = data.get("receipt_no")
            sub_id = data.get("id")
            new_status = data.get("status", "İnceleniyor")

            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                if receipt_no:
                    cursor.execute("UPDATE submissions SET status = ? WHERE receipt_no = ?", (new_status, receipt_no))
                elif sub_id:
                    cursor.execute("UPDATE submissions SET status = ? WHERE id = ?", (new_status, sub_id))
                conn.commit()

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "status": new_status}).encode("utf-8"))
            return

        elif parsed.path == "/api/webhook-settings":
            provider = data.get("provider", "whatsapp_cloud")
            webhook_url = data.get("webhook_url", "").strip()
            auth_token = data.get("auth_token", "").strip()
            template_message = data.get("template_message", "").strip()

            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO webhook_settings (provider, webhook_url, auth_token, template_message, is_active)
                    VALUES (?, ?, ?, ?, 1)
                """, (provider, webhook_url, auth_token, template_message))
                conn.commit()

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "message": "Webhook ayarları kaydedildi."}).encode("utf-8"))
            return

        elif parsed.path == "/api/toplu-hatirlatma":
            target_status = data.get("target_status", [])  # e.g. ["Eksik Evrak Var", "İnceleniyor"]
            channel = data.get("channel", "whatsapp")
            period = data.get("period", "Mart 2026")
            webhook_url = data.get("webhook_url", "").strip()
            auth_token = data.get("auth_token", "").strip()
            custom_template = data.get("template_message", "")

            # Eğer webhook_url verilmemişse DB ayarlarından oku
            if not webhook_url:
                with sqlite3.connect(DB_FILE) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT webhook_url, auth_token, template_message FROM webhook_settings ORDER BY id DESC LIMIT 1")
                    row = cursor.fetchone()
                    if row:
                        webhook_url = row[0] or ""
                        if not auth_token:
                            auth_token = row[1] or ""
                        if not custom_template:
                            custom_template = row[2] or ""

            if not custom_template:
                custom_template = (
                    "Sayın {mukellef} yetkilisi, {donem} dönemi KDV ve Geçici Vergi beyanname hazırlıkları için "
                    "lütfen eksik evraklarınızı mali müşavirlik portalına iletiniz. Ref: {ref_no}"
                )

            # Hedef mükellefleri çek
            with sqlite3.connect(DB_FILE) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                if target_status and isinstance(target_status, list) and len(target_status) > 0:
                    placeholders = ",".join("?" for _ in target_status)
                    cursor.execute(f"SELECT * FROM submissions WHERE status IN ({placeholders})", target_status)
                else:
                    cursor.execute("SELECT * FROM submissions")
                targets = [dict(r) for r in cursor.fetchall()]

            dispatched_logs = []
            for t in targets:
                company = t.get("company_name", "")
                phone = t.get("phone", "")
                ref = t.get("receipt_no", "")
                vkn = t.get("vkn", "")

                msg = custom_template.replace("{mukellef}", company) \
                                     .replace("{donem}", period) \
                                     .replace("{ref_no}", ref) \
                                     .replace("{vkn}", vkn) \
                                     .replace("{portal_url}", "http://localhost:8083/index.html")

                status_code = "SENT"
                response_text = ""

                # Eğer gerçek bir webhook URL tanımlanmışsa HTTP POST at
                if webhook_url and webhook_url.startswith("http"):
                    try:
                        payload = json.dumps({
                            "to": phone,
                            "recipient": company,
                            "vkn": vkn,
                            "message": msg,
                            "channel": channel,
                            "period": period,
                            "receipt_no": ref
                        }).encode("utf-8")

                        headers = {
                            "Content-Type": "application/json; charset=utf-8",
                            "User-Agent": "SMMM-Mukellef-Portal/2.0"
                        }
                        if auth_token:
                            headers["Authorization"] = f"Bearer {auth_token}"

                        req = urllib.request.Request(webhook_url, data=payload, headers=headers, method="POST")
                        with urllib.request.urlopen(req, timeout=5) as response:
                            response_text = response.read().decode("utf-8", errors="replace")
                            status_code = "DELIVERED"
                    except Exception as err:
                        status_code = f"FAILED: {str(err)[:50]}"
                else:
                    status_code = "SIMULATED_SUCCESS"

                # Log kaydet
                with sqlite3.connect(DB_FILE) as conn:
                    c = conn.cursor()
                    c.execute("""
                        INSERT INTO reminder_logs (receipt_no, company_name, phone, channel, status, message, webhook_url)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (ref, company, phone, channel, status_code, msg, webhook_url))
                    conn.commit()

                dispatched_logs.append({
                    "receipt_no": ref,
                    "company_name": company,
                    "phone": phone,
                    "status": status_code,
                    "message": msg
                })

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            resp = {
                "success": True,
                "dispatched_count": len(dispatched_logs),
                "channel": channel,
                "period": period,
                "logs": dispatched_logs
            }
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

def run_server(port=PORT):
    init_db()
    server_address = ("", port)
    httpd = HTTPServer(server_address, EvrakHandler)
    print(f"📊 SMMM Mükellef Evrak Portalı aktif: http://localhost:{port}")
    print(f"📋 Admin Paneli: http://localhost:{port}/admin.html")
    httpd.serve_forever()

if __name__ == "__main__":
    init_db()
    run_server()
