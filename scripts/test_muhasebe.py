# -*- coding: utf-8 -*-
"""
test_muhasebe.py
----------------
SMMM Mükellef Evrak Toplama Portalı entegrasyon ve birim testleri.
Veritabanı işlemleri, UBL-TR e-Fatura XML/ZIP ayrıştırıcı ve
WhatsApp / Webhook otomatik hatırlatma motorunu test eder.
"""

import os
import sys
import json
import sqlite3
import unittest
import io
import zipfile

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from server import init_db, DB_FILE, parse_ubl_xml_content, parse_efatura_files

SAMPLE_UBL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:UBLVersionID>2.1</cbc:UBLVersionID>
  <cbc:CustomizationID>TR1.2</cbc:CustomizationID>
  <cbc:ProfileID>TICARIFATURA</cbc:ProfileID>
  <cbc:ID>GIB2026000000042</cbc:ID>
  <cbc:UUID>a1b2c3d4-e5f6-7890-abcd-ef1234567890</cbc:UUID>
  <cbc:IssueDate>2026-03-24</cbc:IssueDate>
  <cbc:InvoiceTypeCode>SATIS</cbc:InvoiceTypeCode>
  <cbc:DocumentCurrencyCode>TRY</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyName>
        <cbc:Name>Örnek Bilişim ve E-Dönüşüm Hizmetleri A.Ş.</cbc:Name>
      </cac:PartyName>
      <cac:PartyIdentification>
        <cbc:ID schemeID="VKN">1234567890</cbc:ID>
      </cac:PartyIdentification>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyName>
        <cbc:Name>Anadolu Teknoloji ve Lojistik Ltd. Şti.</cbc:Name>
      </cac:PartyName>
      <cac:PartyIdentification>
        <cbc:ID schemeID="VKN">9876543210</cbc:ID>
      </cac:PartyIdentification>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:TaxTotal>
    <cbc:TaxAmount currencyID="TRY">24000.00</cbc:TaxAmount>
    <cac:TaxSubtotal>
      <cbc:TaxAmount currencyID="TRY">24000.00</cbc:TaxAmount>
      <cbc:Percent>20</cbc:Percent>
    </cac:TaxSubtotal>
  </cac:TaxTotal>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="TRY">120000.00</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="TRY">120000.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="TRY">144000.00</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount currencyID="TRY">144000.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
</Invoice>"""

class TestMuhasebePortal(unittest.TestCase):
    def setUp(self):
        init_db()
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("DELETE FROM submissions WHERE receipt_no LIKE 'TESLIM-2026-TEST%'")
            conn.execute("DELETE FROM reminder_logs WHERE receipt_no LIKE 'TESLIM-2026-TEST%'")
            conn.commit()

    def test_database_initialization(self):
        self.assertTrue(os.path.exists(DB_FILE), "muhasebe_evraklar.db oluşturulamadı.")
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='submissions'")
            self.assertIsNotNone(cursor.fetchone(), "'submissions' tablosu bulunamadı.")

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reminder_logs'")
            self.assertIsNotNone(cursor.fetchone(), "'reminder_logs' tablosu bulunamadı.")

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='webhook_settings'")
            self.assertIsNotNone(cursor.fetchone(), "'webhook_settings' tablosu bulunamadı.")

            cursor.execute("PRAGMA table_info(submissions)")
            cols = [r[1] for r in cursor.fetchall()]
            for c in ["parsed_invoices", "total_matrah", "total_kdv", "total_payable"]:
                self.assertIn(c, cols, f"Sütun '{c}' submissions tablosunda eksik.")

    def test_document_submission_flow(self):
        receipt_no = "TESLIM-2026-TEST01"
        company = "Ornek Lojistik Ltd. Sti."
        vkn = "9988776655"
        docs = ["Alis Faturalari (24)", "Banka Ekstresi", "Z-Raporu"]
        invoices = [
            {
                "fatura_no": "GIB2026000000042",
                "matrah": 120000.0,
                "kdv_tutar": 24000.0,
                "odenecek_tutar": 144000.0
            }
        ]

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
                company,
                vkn,
                "Mehmet Ozturk",
                "05559876543",
                "Mart 2026",
                json.dumps(docs),
                "Tum subat faturalari eklendi.",
                3,
                json.dumps(invoices),
                120000.0,
                24000.0,
                144000.0
            ))
            conn.commit()

            cursor.execute("SELECT * FROM submissions WHERE receipt_no=?", (receipt_no,))
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[1], receipt_no)
            self.assertEqual(row[2], company)
            self.assertEqual(row[3], vkn)
            self.assertEqual(row[6], "Mart 2026")
            self.assertEqual(row[9], 3) # files_count
            self.assertEqual(row[13], 120000.0) # total_matrah
            self.assertEqual(row[14], 24000.0) # total_kdv
            self.assertEqual(row[15], 144000.0) # total_payable

    def test_ubl_xml_parsing(self):
        inv = parse_ubl_xml_content(SAMPLE_UBL_XML)
        self.assertIsNotNone(inv)
        self.assertEqual(inv["fatura_no"], "GIB2026000000042")
        self.assertEqual(inv["tarih"], "2026-03-24")
        self.assertEqual(inv["fatura_tipi"], "SATIS")
        self.assertEqual(inv["satici_vkn"], "1234567890")
        self.assertEqual(inv["satici_unvan"], "Örnek Bilişim ve E-Dönüşüm Hizmetleri A.Ş.")
        self.assertEqual(inv["alici_vkn"], "9876543210")
        self.assertEqual(inv["matrah"], 120000.0)
        self.assertEqual(inv["kdv_tutar"], 24000.0)
        self.assertEqual(inv["odenecek_tutar"], 144000.0)
        self.assertEqual(len(inv["kdv_oranlari"]), 1)
        self.assertEqual(inv["kdv_oranlari"][0]["oran"], 20.0)

    def test_zip_package_parsing(self):
        # In-memory ZIP containing an XML invoice
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("fatura1.xml", SAMPLE_UBL_XML)
            zf.writestr("fatura2.xml", SAMPLE_UBL_XML.replace("GIB2026000000042", "GIB2026000000043"))

        result = parse_efatura_files(zip_buffer.getvalue(), "faturalar.zip")
        self.assertTrue(result["success"])
        self.assertEqual(result["summary"]["count"], 2)
        self.assertEqual(result["summary"]["total_matrah"], 240000.0)
        self.assertEqual(result["summary"]["total_kdv"], 48000.0)
        self.assertEqual(result["summary"]["total_payable"], 288000.0)

    def test_bulk_reminder_and_webhook_formatting(self):
        template = "Sayın {mukellef} yetkilisi, {donem} dönemi KDV evraklarınız için son gün. Ref: {ref_no}"
        company = "Yıldız Mimarlık"
        period = "Mart 2026"
        ref = "TESLIM-2026-TEST99"

        msg = template.replace("{mukellef}", company).replace("{donem}", period).replace("{ref_no}", ref)
        self.assertIn("Yıldız Mimarlık", msg)
        self.assertIn("Mart 2026", msg)
        self.assertIn("TESLIM-2026-TEST99", msg)

        # Reminder log persist test
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO reminder_logs (receipt_no, company_name, phone, channel, status, message, webhook_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (ref, company, "05332221100", "whatsapp", "SIMULATED_SUCCESS", msg, "https://api.test/webhook"))
            conn.commit()

            c.execute("SELECT * FROM reminder_logs WHERE receipt_no=?", (ref,))
            row = c.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[1], ref)
            self.assertEqual(row[2], company)
            self.assertEqual(row[5], "SIMULATED_SUCCESS")

    def test_status_update(self):
        receipt_no = "TESLIM-2026-TESTSTATUS"
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO submissions (receipt_no, company_name, status)
                VALUES (?, ?, ?)
            """, (receipt_no, "Test Sirketi", "İnceleniyor"))
            conn.commit()

            c.execute("UPDATE submissions SET status = ? WHERE receipt_no = ?", ("Muhasebeleştirildi", receipt_no))
            conn.commit()

            c.execute("SELECT status FROM submissions WHERE receipt_no=?", (receipt_no,))
            status = c.fetchone()[0]
            self.assertEqual(status, "Muhasebeleştirildi")

if __name__ == "__main__":
    print("=" * 60)
    print("  SMMM MÜKELLEF EVRAK PORTAL TEST SÜİTİ")
    print("=" * 60)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMuhasebePortal)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():
        print("\n✅ TÜM TESTLER BAŞARIYLA GEÇTİ!")
        sys.exit(0)
    else:
        print("\n❌ TEST BAŞARISIZ!")
        sys.exit(1)
