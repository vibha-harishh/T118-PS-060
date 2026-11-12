import os
import sys
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from decimal import Decimal
from typing import Dict, Any

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db import init_db, get_db_connection, transaction
from backend.config import paise_to_rupees, format_rupees
from backend.partners import register_partner, ingest_partners_csv
from backend.tasks import ingest_slots_csv, ingest_task_events_csv
from backend.commands import execute_command_line, execute_command_script
from backend.settlement import run_settlement_batch, is_marketplace_active
from backend.reports import (
    generate_weekly_statements_csv,
    generate_batch_summary_csv,
    generate_ledger_csv,
    generate_tds_summary_csv
)

PORT = int(os.environ.get("PYTHON_PORT", "5050"))

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)

class PayoutAPIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Concise logging
        sys.stderr.write(f"[API] {args[0]} {args[1]}\n")

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def _send_json(self, status_code: int, data: Any):
        body = json.dumps(data, cls=JSONEncoder).encode("utf-8")
        self.send_response(status_code)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_csv(self, filename: str, csv_data: str):
        body = csv_data.encode("utf-8")
        self.send_response(200)
        self._send_cors_headers()
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body_json(self) -> Dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length).decode("utf-8")
        return json.loads(raw)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # 1. System Status
            if path == "/api/status":
                cursor.execute("SELECT count(*) as cnt FROM partners")
                partners_count = cursor.fetchone()["cnt"]
                cursor.execute("SELECT count(*) as cnt FROM slots")
                slots_count = cursor.fetchone()["cnt"]
                cursor.execute("SELECT count(*) as cnt FROM task_events")
                tasks_count = cursor.fetchone()["cnt"]
                cursor.execute("SELECT count(*) as cnt FROM settlement_batches")
                batches_count = cursor.fetchone()["cnt"]
                cursor.execute("SELECT count(*) as cnt FROM weekly_statements")
                statements_count = cursor.fetchone()["cnt"]
                cursor.execute("SELECT count(*) as cnt FROM ledger_entries")
                ledger_count = cursor.fetchone()["cnt"]

                # Preloaded files check
                asset_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public", "assets", "aistudio"))
                has_preloaded_partners = os.path.exists(os.path.join(asset_dir, "partners_76ec20c2.csv"))
                has_preloaded_slots = os.path.exists(os.path.join(asset_dir, "slots_c936832b.csv"))
                has_preloaded_commands = os.path.exists(os.path.join(asset_dir, "commands_11750b4b.txt"))

                cursor.execute("SELECT * FROM marketplace_periods ORDER BY effective_date DESC LIMIT 1")
                mp_row = cursor.fetchone()

                self._send_json(200, {
                    "partners_count": partners_count,
                    "slots_count": slots_count,
                    "tasks_count": tasks_count,
                    "batches_count": batches_count,
                    "statements_count": statements_count,
                    "ledger_count": ledger_count,
                    "marketplace_mode": bool(mp_row["is_active"]) if mp_row else False,
                    "marketplace_date": mp_row["effective_date"] if mp_row else None,
                    "preloaded": {
                        "partners": has_preloaded_partners,
                        "slots": has_preloaded_slots,
                        "commands": has_preloaded_commands
                    }
                })

            # 2. Partners List
            elif path == "/api/partners":
                cursor.execute("""
                    SELECT p.*,
                           COALESCE((SELECT SUM(net_payable_paise) FROM weekly_statements WHERE partner_id = p.partner_id AND status = 'PAID'), 0) as paid_in_batches_paise,
                           COALESCE((SELECT SUM(tds_paise) FROM weekly_statements WHERE partner_id = p.partner_id), 0) as tds_in_batches_paise
                    FROM partners p
                    ORDER BY p.partner_id ASC
                """)
                partners = [dict(r) for r in cursor.fetchall()]
                # Format money
                for p in partners:
                    p["fy_paid_before_rupees"] = float(paise_to_rupees(p["fy_paid_before_paise"]))
                    p["fy_tds_before_rupees"] = float(paise_to_rupees(p["fy_tds_before_paise"]))
                    p["equipment_recovered_rupees"] = float(paise_to_rupees(p["equipment_recovered_before_paise"]))
                    p["paid_in_batches_rupees"] = float(paise_to_rupees(p["paid_in_batches_paise"]))
                    p["tds_in_batches_rupees"] = float(paise_to_rupees(p["tds_in_batches_paise"]))
                self._send_json(200, {"partners": partners})

            # 3. Single Partner Detail
            elif path.startswith("/api/partners/"):
                partner_id = path.replace("/api/partners/", "").strip()
                cursor.execute("SELECT * FROM partners WHERE partner_id = ?", (partner_id,))
                p = cursor.fetchone()
                if not p:
                    self._send_json(404, {"error": "Partner not found"})
                    return
                p_dict = dict(p)
                # Fetch partner's weekly statements
                cursor.execute("""
                    SELECT * FROM weekly_statements WHERE partner_id = ? ORDER BY week_start ASC
                """, (partner_id,))
                stmts = [dict(r) for r in cursor.fetchall()]
                for s in stmts:
                    s["task_earnings_rupees"] = float(paise_to_rupees(s["task_earnings_paise"]))
                    s["incentive_rupees"] = float(paise_to_rupees(s["incentive_paise"]))
                    s["gross_rupees"] = float(paise_to_rupees(s["gross_paise"]))
                    s["penalties_rupees"] = float(paise_to_rupees(s["penalties_paise"]))
                    s["tds_base_rupees"] = float(paise_to_rupees(s["tds_base_paise"]))
                    s["tds_rupees"] = float(paise_to_rupees(s["tds_paise"]))
                    s["net_payable_rupees"] = float(paise_to_rupees(s["net_payable_paise"]))
                    s["equipment_deduction_rupees"] = float(paise_to_rupees(s["equipment_deduction_paise"]))
                    s["carry_in_rupees"] = float(paise_to_rupees(s["carry_in_paise"]))

                # Fetch ledger entries
                cursor.execute("""
                    SELECT * FROM ledger_entries WHERE partner_id = ? ORDER BY id ASC
                """, (partner_id,))
                ledgers = [dict(r) for r in cursor.fetchall()]
                for l in ledgers:
                    l["amount_rupees"] = float(paise_to_rupees(l["amount_paise"]))
                    l["earned_to_date_rupees"] = float(paise_to_rupees(l["earned_to_date_paise"]))
                    l["withheld_to_date_rupees"] = float(paise_to_rupees(l["withheld_to_date_paise"]))
                    l["paid_to_date_rupees"] = float(paise_to_rupees(l["paid_to_date_paise"]))
                    l["recovered_to_date_rupees"] = float(paise_to_rupees(l["recovered_to_date_paise"]))

                self._send_json(200, {
                    "partner": p_dict,
                    "statements": stmts,
                    "ledger": ledgers
                })

            # 4. Weekly Statements
            elif path == "/api/statements":
                week_filter = params.get("week_start", [None])[0]
                status_filter = params.get("status", [None])[0]
                query = "SELECT * FROM weekly_statements WHERE 1=1"
                qargs = []
                if week_filter:
                    query += " AND week_start = ?"
                    qargs.append(week_filter)
                if status_filter:
                    query += " AND status = ?"
                    qargs.append(status_filter)
                query += " ORDER BY week_start ASC, partner_id ASC"

                cursor.execute(query, qargs)
                stmts = [dict(r) for r in cursor.fetchall()]
                for s in stmts:
                    s["task_earnings_rupees"] = float(paise_to_rupees(s["task_earnings_paise"]))
                    s["incentive_rupees"] = float(paise_to_rupees(s["incentive_paise"]))
                    s["gross_rupees"] = float(paise_to_rupees(s["gross_paise"]))
                    s["penalties_rupees"] = float(paise_to_rupees(s["penalties_paise"]))
                    s["penalty_cap_rupees"] = float(paise_to_rupees(s["penalty_cap_paise"]))
                    s["adjustments_rupees"] = float(paise_to_rupees(s["adjustments_paise"]))
                    s["tds_base_rupees"] = float(paise_to_rupees(s["tds_base_paise"]))
                    s["tds_rupees"] = float(paise_to_rupees(s["tds_paise"]))
                    s["equipment_deduction_rupees"] = float(paise_to_rupees(s["equipment_deduction_paise"]))
                    s["carry_in_rupees"] = float(paise_to_rupees(s["carry_in_paise"]))
                    s["net_payable_rupees"] = float(paise_to_rupees(s["net_payable_paise"]))

                self._send_json(200, {"statements": stmts})

            # 5. Settlement Batches
            elif path == "/api/batches":
                cursor.execute("SELECT * FROM settlement_batches ORDER BY batch_date ASC")
                batches = [dict(r) for r in cursor.fetchall()]
                for b in batches:
                    b["amount_paid_rupees"] = float(paise_to_rupees(b["amount_paid_paise"]))
                    b["amount_held_rupees"] = float(paise_to_rupees(b["amount_held_paise"]))
                    b["carried_forward_rupees"] = float(paise_to_rupees(b["carried_forward_paise"]))
                    b["tds_total_rupees"] = float(paise_to_rupees(b["tds_total_paise"]))
                self._send_json(200, {"batches": batches})

            # 6. Full Ledger
            elif path == "/api/ledger":
                partner_filter = params.get("partner_id", [None])[0]
                query = "SELECT * FROM ledger_entries"
                qargs = []
                if partner_filter:
                    query += " WHERE partner_id = ?"
                    qargs.append(partner_filter)
                query += " ORDER BY id DESC LIMIT 500"

                cursor.execute(query, qargs)
                ledgers = [dict(r) for r in cursor.fetchall()]
                for l in ledgers:
                    l["amount_rupees"] = float(paise_to_rupees(l["amount_paise"]))
                    l["earned_to_date_rupees"] = float(paise_to_rupees(l["earned_to_date_paise"]))
                    l["withheld_to_date_rupees"] = float(paise_to_rupees(l["withheld_to_date_paise"]))
                    l["paid_to_date_rupees"] = float(paise_to_rupees(l["paid_to_date_paise"]))
                    l["recovered_to_date_rupees"] = float(paise_to_rupees(l["recovered_to_date_paise"]))
                self._send_json(200, {"ledger": ledgers})

            # 7. Form 26Q TDS Summary
            elif path == "/api/reports/tds_summary":
                fy = params.get("fy", ["2026-27"])[0]
                quarter = params.get("quarter", ["Q2"])[0]
                csv_data = generate_tds_summary_csv(conn, fy, quarter)
                # Parse to JSON as well for display
                lines = csv_data.strip().splitlines()
                rows = []
                if len(lines) > 1:
                    headers = lines[0].split(",")
                    for l in lines[1:]:
                        vals = l.split(",")
                        rows.append(dict(zip(headers, vals)))
                self._send_json(200, {"fy": fy, "quarter": quarter, "summary": rows})

            # 8. Download Evaluation CSV Files
            elif path.startswith("/api/reports/download/"):
                report_type = path.replace("/api/reports/download/", "").strip()
                if report_type == "weekly_statements.csv":
                    csv_data = generate_weekly_statements_csv(conn)
                    self._send_csv("weekly_statements.csv", csv_data)
                elif report_type == "batch_summary.csv":
                    csv_data = generate_batch_summary_csv(conn)
                    self._send_csv("batch_summary.csv", csv_data)
                elif report_type == "ledger.csv":
                    csv_data = generate_ledger_csv(conn)
                    self._send_csv("ledger.csv", csv_data)
                elif report_type == "tds_summary_q2.csv":
                    csv_data = generate_tds_summary_csv(conn, "2026-27", "Q2")
                    self._send_csv("tds_summary_2026-27_Q2.csv", csv_data)
                elif report_type == "tds_summary_q3.csv":
                    csv_data = generate_tds_summary_csv(conn, "2026-27", "Q3")
                    self._send_csv("tds_summary_2026-27_Q3.csv", csv_data)
                else:
                    self._send_json(404, {"error": f"Unknown report type {report_type}"})

            # 9. Ingested Tasks Overview / Sample
            elif path == "/api/tasks":
                limit = int(params.get("limit", [50])[0])
                cursor.execute("""
                    SELECT t.*, p.partner_name, s.surge, s.rain
                    FROM task_events t
                    LEFT JOIN partners p ON t.partner_id = p.partner_id
                    LEFT JOIN slots s ON t.slot_id = s.slot_id
                    ORDER BY t.event_ts ASC LIMIT ?
                """, (limit,))
                tasks = [dict(r) for r in cursor.fetchall()]
                for t in tasks:
                    t["task_earnings_rupees"] = float(paise_to_rupees(t["task_earnings_paise"]))
                self._send_json(200, {"tasks": tasks})

            else:
                self._send_json(404, {"error": f"Route not found: {path}"})

            conn.close()

        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        try:
            body = self._read_body_json()

            # 1. Initialize or Reset DB
            if path == "/api/init-db":
                drop_all = body.get("drop_all", False)
                init_db(drop_all=drop_all)
                self._send_json(200, {"status": "SUCCESS", "message": "Database initialized"})

            # 2. Ingest Preloaded Datasets
            elif path == "/api/ingest/preloaded":
                asset_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public", "assets", "aistudio"))
                partners_path = os.path.join(asset_dir, "partners_76ec20c2.csv")
                slots_path = os.path.join(asset_dir, "slots_c936832b.csv")

                with transaction() as conn:
                    # Ingest partners
                    with open(partners_path, "r", encoding="utf-8") as f:
                        partners_res = ingest_partners_csv(conn, f.read())
                    # Ingest slots
                    with open(slots_path, "r", encoding="utf-8") as f:
                        slots_res = ingest_slots_csv(conn, f.read())

                self._send_json(200, {
                    "status": "SUCCESS",
                    "partners": partners_res,
                    "slots": slots_res
                })

            # 3. Ingest Partners CSV
            elif path == "/api/ingest/partners":
                csv_content = body.get("csv_content", "")
                with transaction() as conn:
                    result = ingest_partners_csv(conn, csv_content)
                self._send_json(200, {"status": "SUCCESS", "result": result})

            # 4. Ingest Slots CSV
            elif path == "/api/ingest/slots":
                csv_content = body.get("csv_content", "")
                with transaction() as conn:
                    result = ingest_slots_csv(conn, csv_content)
                self._send_json(200, {"status": "SUCCESS", "result": result})

            # 5. Ingest Task Events CSV
            elif path == "/api/ingest/tasks":
                csv_content = body.get("csv_content", "")
                with transaction() as conn:
                    result = ingest_task_events_csv(conn, csv_content)
                self._send_json(200, {"status": "SUCCESS", "result": result})

            # 6. Execute Preloaded Commands file
            elif path == "/api/commands/execute-preloaded":
                asset_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public", "assets", "aistudio"))
                cmd_path = os.path.join(asset_dir, "commands_11750b4b.txt")
                with open(cmd_path, "r", encoding="utf-8") as f:
                    content = f.read()
                with transaction() as conn:
                    results = execute_command_script(conn, content)
                self._send_json(200, {"status": "SUCCESS", "total_executed": len(results), "results": results})

            # 7. Execute Custom Commands text
            elif path == "/api/commands/execute":
                content = body.get("commands", "")
                with transaction() as conn:
                    results = execute_command_script(conn, content)
                self._send_json(200, {"status": "SUCCESS", "total_executed": len(results), "results": results})

            # 8. Execute Single Command Line
            elif path == "/api/commands/single":
                line = body.get("command", "")
                with transaction() as conn:
                    result = execute_command_line(conn, line)
                self._send_json(200, result)

            # 9. Direct Settlement Run Batch
            elif path == "/api/batches/run":
                batch_date = body.get("batch_date", "")
                with transaction() as conn:
                    summary = run_settlement_batch(conn, batch_date)
                self._send_json(200, {"status": "SUCCESS", "batch": summary})

            else:
                self._send_json(404, {"error": f"Route not found: {path}"})

        except Exception as e:
            self._send_json(500, {"error": str(e)})
def load_preloaded_task_events():
    """Load official task events once, only when the task table is empty."""
    asset_dir = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "public",
            "assets",
            "aistudio"
        )
    )
    task_path = os.path.join(asset_dir, "task_events.csv")

    if not os.path.exists(task_path):
        raise FileNotFoundError(
            f"Task dataset not found: {task_path}"
        )

    with transaction() as conn:
        task_count = conn.execute(
            "SELECT COUNT(*) FROM task_events"
        ).fetchone()[0]

        if task_count > 0:
            print(
                f"[PayoutEngine] Task events already loaded: "
                f"{task_count}. Skipping import."
            )
            return

        partner_count = conn.execute(
            "SELECT COUNT(*) FROM partners"
        ).fetchone()[0]

        slot_count = conn.execute(
            "SELECT COUNT(*) FROM slots"
        ).fetchone()[0]

        if partner_count == 0 or slot_count == 0:
            raise RuntimeError(
                "Partners or slots are missing. "
                "Cannot safely import task events."
            )

        with open(task_path, "r", encoding="utf-8") as file:
            result = ingest_task_events_csv(conn, file.read())

        if result["errors"]:
            raise RuntimeError(
                f"Task import failed. "
                f"{len(result['errors'])} row errors. "
                f"First errors: {result['errors'][:5]}"
            )

        print(
            f"[PayoutEngine] Task events imported: "
            f"{result['successful']} successful, "
            f"{result['duplicates_skipped']} duplicates skipped."
        )
def start_server():
    init_db(drop_all=False)
    server_address = ("0.0.0.0", PORT)
    httpd = ThreadedHTTPServer(server_address, PayoutAPIHandler)
    sys.stderr.write(f"[PayoutEngine] Python API Server running on port {PORT}\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()

if __name__ == "__main__":
    start_server()
