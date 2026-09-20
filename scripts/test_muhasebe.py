# -*- coding: utf-8 -*-
"""
test_muhasebe.py
----------------
SMMM Mükellef Evrak Toplama Portalı entegrasyon ve birim testleri.
"""

import os
import sys
import json
import sqlite3
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from server import init_db, DB_FILE

class TestMuhasebePortal(unittest.TestCase):
    def setUp(self):
        init_db()
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("DELETE FROM submissions WHERE receipt_no LIKE 'TESLIM-2026-TEST%'")
            conn.commit()

    def test_database_initialization(self):
        self.assertTrue(os.path.exists(DB_FILE), "muhasebe_evraklar.db olusturulamadi.")
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='submissions'")
            table = cursor.fetchone()
            self.assertIsNotNone(table, "'submissions' tablosu bulunamadi.")

    def test_document_submission_flow(self):
        receipt_no = "TESLIM-2026-TEST01"
        company = "Ornek Lojistik Ltd. Sti."
        vkn = "9988776655"
        docs = ["Alis Faturalari (24)", "Banka Ekstresi", "Z-Raporu"]

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO submissions (
                    receipt_no, company_name, vkn, contact_name, phone,
                    period, delivered_docs, notes, files_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                receipt_no,
                company,
                vkn,
                "Mehmet Ozturk",
                "05559876543",
                "Mart 2026",
                json.dumps(docs),
                "Tum subat faturalari eklendi.",
                3
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
