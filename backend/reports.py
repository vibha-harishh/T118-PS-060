"""Report generation module producing evaluation CSVs and statement summaries."""
import csv
import io
import sqlite3
from typing import Dict, Any, List

from backend.config import paise_to_rupees, format_rupees

def generate_weekly_statements_csv(conn: sqlite3.Connection) -> str:
    """
    Generate weekly_statements.csv string:
    partner_id, week_start, completed, cancelled_by_partner, cancelled_by_customer,
    cancellation_rate_pct, avg_rating, task_earnings, incentive, gross, penalties,
    penalty_cap, adjustments, tds_base, tds_section, tds_rate_pct, tds,
    equipment_deduction, carry_in, net_payable, status
    Sorted by week_start then partner_id.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM weekly_statements
        ORDER BY week_start ASC, partner_id ASC
    """)
    rows = cursor.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "partner_id", "week_start", "completed", "cancelled_by_partner", "cancelled_by_customer",
        "cancellation_rate_pct", "avg_rating", "task_earnings", "incentive", "gross",
        "penalties", "penalty_cap", "adjustments", "tds_base", "tds_section", "tds_rate_pct",
        "tds", "equipment_deduction", "carry_in", "net_payable", "status"
    ])

    for r in rows:
        writer.writerow([
            r["partner_id"],
            r["week_start"],
            r["completed"],
            r["cancelled_by_partner"],
            r["cancelled_by_customer"],
            f"{r['cancellation_rate_pct']:.2f}",
            f"{r['avg_rating']:.2f}",
            format_rupees(r["task_earnings_paise"]),
            format_rupees(r["incentive_paise"]),
            format_rupees(r["gross_paise"]),
            format_rupees(r["penalties_paise"]),
            format_rupees(r["penalty_cap_paise"]),
            format_rupees(r["adjustments_paise"]),
            format_rupees(r["tds_base_paise"]),
            r["tds_section"],
            f"{r['tds_rate_pct']:.2f}",
            format_rupees(r["tds_paise"]),
            format_rupees(r["equipment_deduction_paise"]),
            format_rupees(r["carry_in_paise"]),
            format_rupees(r["net_payable_paise"]),
            r["status"]
        ])

    return output.getvalue()

def generate_batch_summary_csv(conn: sqlite3.Connection) -> str:
    """
    Generate batch_summary.csv string:
    batch_date, partners_paid, amount_paid, partners_held, amount_held,
    carried_forward, retries, tds_total
    One row per RUN_BATCH.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM settlement_batches ORDER BY batch_date ASC")
    rows = cursor.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "batch_date", "partners_paid", "amount_paid", "partners_held",
        "amount_held", "carried_forward", "retries", "tds_total"
    ])

    for r in rows:
        writer.writerow([
            r["batch_date"],
            r["partners_paid"],
            format_rupees(r["amount_paid_paise"]),
            r["partners_held"],
            format_rupees(r["amount_held_paise"]),
            format_rupees(r["carried_forward_paise"]),
            r["retries"],
            format_rupees(r["tds_total_paise"])
        ])

    return output.getvalue()

def generate_ledger_csv(conn: sqlite3.Connection) -> str:
    """
    Generate ledger.csv string:
    partner_id, entry_ts, entry_type, week_start, amount, earned_to_date,
    withheld_to_date, paid_to_date, recovered_to_date
    One row per ledger movement, in posting order.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ledger_entries ORDER BY id ASC")
    rows = cursor.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "partner_id", "entry_ts", "entry_type", "week_start", "amount",
        "earned_to_date", "withheld_to_date", "paid_to_date", "recovered_to_date"
    ])

    for r in rows:
        writer.writerow([
            r["partner_id"],
            r["entry_ts"],
            r["entry_type"],
            r["week_start"] or "",
            format_rupees(r["amount_paise"]),
            format_rupees(r["earned_to_date_paise"]),
            format_rupees(r["withheld_to_date_paise"]),
            format_rupees(r["paid_to_date_paise"]),
            format_rupees(r["recovered_to_date_paise"])
        ])

    return output.getvalue()

def get_quarter_date_bounds(fy: str, quarter: str) -> tuple[str, str]:
    """
    Given FY e.g. '2026-27' and quarter 'Q1', 'Q2', 'Q3', 'Q4',
    return start_date and end_date (inclusive) for settlement batches.
    Indian FY starts April 1:
    - Q1: Apr 1 - Jun 30
    - Q2: Jul 1 - Sep 30
    - Q3: Oct 1 - Dec 31
    - Q4: Jan 1 - Mar 31
    """
    start_year = int(fy.split("-")[0])
    next_year = start_year + 1

    if quarter == "Q1":
        return f"{start_year}-04-01", f"{start_year}-06-30"
    elif quarter == "Q2":
        return f"{start_year}-07-01", f"{start_year}-09-30"
    elif quarter == "Q3":
        return f"{start_year}-10-01", f"{start_year}-12-31"
    elif quarter == "Q4":
        return f"{next_year}-01-01", f"{next_year}-03-31"
    else:
        raise ValueError(f"Invalid quarter '{quarter}'")

def generate_tds_summary_csv(conn: sqlite3.Connection, fy: str, quarter: str) -> str:
    """
    Generate Form 26Q-style summary for a given quarter:
    fy, quarter, partner_id, pan, section, rate_pct, amount_paid, tds_deducted
    One row per section per partner where TDS was deducted or payments made.
    """
    start_date, end_date = get_quarter_date_bounds(fy, quarter)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            w.partner_id,
            p.pan,
            w.tds_section,
            w.tds_rate_pct,
            SUM(w.tds_base_paise) as total_base_paise,
            SUM(w.tds_paise) as total_tds_paise
        FROM weekly_statements w
        JOIN partners p ON w.partner_id = p.partner_id
        WHERE w.batch_date >= ? AND w.batch_date <= ? AND w.tds_section != 'NONE'
        GROUP BY w.partner_id, p.pan, w.tds_section, w.tds_rate_pct
        ORDER BY w.partner_id ASC, w.tds_section ASC
    """, (start_date, end_date))
    rows = cursor.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "fy", "quarter", "partner_id", "pan", "section", "rate_pct", "amount_paid", "tds_deducted"
    ])

    for r in rows:
        writer.writerow([
            fy,
            quarter,
            r["partner_id"],
            r["pan"] or "",
            r["tds_section"],
            f"{r['tds_rate_pct']:.2f}",
            format_rupees(r["total_base_paise"]),
            format_rupees(r["total_tds_paise"])
        ])

    return output.getvalue()
