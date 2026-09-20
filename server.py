# -*- coding: utf-8 -*-
"""
server.py
---------
SMMM Mükellef Aylık Evrak Toplama Portalı - Sıfır Bağımlılıklı Python Sunucusu.
SQLite veritabanı ile teslim edilen evrakları ve dosyaları saklar.
"""

import os
import sys
import json
import sqlite3
import random
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PORT = 8083
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "muhasebe_evraklar.db")

def init_db():
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

class EvrakHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
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
                self.wfile.write(json.dumps(rows, ensure_ascii=False).encode("utf-8"))
            return

        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/evrak-teslim":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
            except Exception:
                data = {}

            receipt_no = f"TESLIM-2026-{random.randint(1000, 9999)}"
            docs_json = json.dumps(data.get("delivered_docs", []), ensure_ascii=False)

            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO submissions (
                        receipt_no, company_name, vkn, contact_name, phone,
                        period, delivered_docs, notes, files_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    receipt_no,
                    data.get("company_name", ""),
                    data.get("vkn", ""),
                    data.get("contact_name", ""),
                    data.get("phone", ""),
                    data.get("period", ""),
                    docs_json,
                    data.get("notes", ""),
                    int(data.get("files_count", 0))
                ))
                conn.commit()

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            resp = {
                "success": True,
                "receipt_no": receipt_no,
                "message": "Aylık evrak teslim bildiriminiz başarıyla kaydedilmiştir."
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
