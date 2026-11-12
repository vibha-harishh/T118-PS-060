"""Commands processor executing command instructions sequentially."""
import sqlite3
from decimal import Decimal
from typing import Dict, Any, List, Optional

from backend.config import (
    rupees_to_paise,
    paise_to_rupees,
    MAX_ADJUSTMENT_PAISE,
    BANK_RETRY_CHARGE_PAISE,
    MAX_BANK_RETRIES
)
from backend.settlement import run_settlement_batch
from backend.ledger import post_ledger_entry

def execute_command_line(conn: sqlite3.Connection, line: str) -> Dict[str, Any]:
    """Execute a single command string formatted as COMMAND_NAME|arg1|arg2|..."""
    line = line.strip()
    if not line or line.startswith("#"):
        return {"status": "SKIPPED", "line": line}

    parts = line.split("|")
    cmd = parts[0].strip()
    args = parts[1:]
    cursor = conn.cursor()

    if cmd == "RUN_BATCH":
        batch_date = args[0].strip()
        summary = run_settlement_batch(conn, batch_date)
        return {"status": "SUCCESS", "cmd": cmd, "batch_date": batch_date, "summary": summary}

    elif cmd == "BANK_RETURN":
        # partner_id|batch_date|ts|reason
        partner_id = args[0].strip()
        batch_date = args[1].strip()
        ts = args[2].strip()
        reason = args[3].strip() if len(args) > 3 else "RETURNED"

        # Check partner's current retry count
        cursor.execute("SELECT bank_retry_count, is_held_manual FROM partners WHERE partner_id = ?", (partner_id,))
        partner = cursor.fetchone()
        if not partner:
            return {"status": "ERROR", "message": f"Partner {partner_id} not found"}

        current_retries = partner['bank_retry_count'] + 1
        new_held = partner['is_held_manual']

        # If retries exceeded (2 retries exhausted), mark HELD_MANUAL
        if current_retries > MAX_BANK_RETRIES:
            new_held = 1

        cursor.execute("""
            UPDATE partners SET bank_retry_count = ?, is_held_manual = ?,
                   manual_hold_reason = CASE WHEN ? = 1 THEN 'BANK_RETRIES_EXHAUSTED' ELSE manual_hold_reason END
            WHERE partner_id = ?
        """, (current_retries, new_held, new_held, partner_id))

        cursor.execute("""
            INSERT INTO bank_returns (partner_id, batch_date, return_ts, reason, retry_number)
            VALUES (?, ?, ?, ?, ?)
        """, (partner_id, batch_date, ts, reason, current_retries))

        # Look up previous statement payout amount
        cursor.execute("""
            SELECT net_payable_paise, week_start FROM weekly_statements
            WHERE partner_id = ? AND batch_date = ?
        """, (partner_id, batch_date))
        stmt = cursor.fetchone()
        returned_amount = stmt['net_payable_paise'] if stmt else 0
        week_start = stmt['week_start'] if stmt else None

        # Reversal in ledger
        if returned_amount > 0:
            post_ledger_entry(
                conn=conn, partner_id=partner_id, entry_ts=ts, entry_type="PAYOUT_RETURN",
                week_start=week_start, amount_paise=returned_amount, paid_delta_paise=-returned_amount
            )
        # Bank charge for retry
        post_ledger_entry(
            conn=conn, partner_id=partner_id, entry_ts=ts, entry_type="BANK_CHARGE",
            week_start=week_start, amount_paise=-BANK_RETRY_CHARGE_PAISE
        )

        return {
            "status": "SUCCESS", "cmd": cmd, "partner_id": partner_id,
            "retry_number": current_retries, "held_manual": bool(new_held)
        }

    elif cmd == "BANK_VERIFIED":
        # partner_id|ts
        partner_id = args[0].strip()
        ts = args[1].strip()
        cursor.execute("UPDATE partners SET bank_status = 'VERIFIED' WHERE partner_id = ?", (partner_id,))
        return {"status": "SUCCESS", "cmd": cmd, "partner_id": partner_id}

    elif cmd == "PAN_UPDATE":
        # partner_id|ts|pan
        partner_id = args[0].strip()
        ts = args[1].strip()
        pan = args[2].strip()
        cursor.execute("UPDATE partners SET pan = ?, pan_status = 'VALID' WHERE partner_id = ?", (pan, partner_id))
        return {"status": "SUCCESS", "cmd": cmd, "partner_id": partner_id, "pan": pan}

    elif cmd == "HOLD":
        # partner_id|ts|reason
        partner_id = args[0].strip()
        ts = args[1].strip()
        reason = args[2].strip() if len(args) > 2 else "MANUAL_HOLD"
        cursor.execute("""
            UPDATE partners SET is_held_manual = 1, manual_hold_reason = ? WHERE partner_id = ?
        """, (reason, partner_id))
        return {"status": "SUCCESS", "cmd": cmd, "partner_id": partner_id, "reason": reason}

    elif cmd == "RELEASE":
        # partner_id|ts
        partner_id = args[0].strip()
        ts = args[1].strip()
        cursor.execute("""
            UPDATE partners SET is_held_manual = 0, manual_hold_reason = NULL WHERE partner_id = ?
        """, (partner_id,))
        return {"status": "SUCCESS", "cmd": cmd, "partner_id": partner_id}

    elif cmd == "COMPLAINT":
        # partner_id|task_id|ts|reason
        partner_id = args[0].strip()
        task_id = args[1].strip()
        ts = args[2].strip()
        reason = args[3].strip() if len(args) > 3 else "CUSTOMER_COMPLAINT"

        # Determine task's week_start
        cursor.execute("SELECT week_start FROM task_events WHERE task_id = ? LIMIT 1", (task_id,))
        trow = cursor.fetchone()
        week_start = trow['week_start'] if trow else None

        if not week_start:
            # Fallback: estimate week from complaint timestamp if task event isn't indexed yet
            from backend.calculations import get_week_start
            week_start = get_week_start(ts)

        cursor.execute("""
            INSERT INTO complaints (partner_id, task_id, complaint_ts, reason, week_start)
            VALUES (?, ?, ?, ?, ?)
        """, (partner_id, task_id, ts, reason, week_start))
        return {"status": "SUCCESS", "cmd": cmd, "partner_id": partner_id, "task_id": task_id, "week_start": week_start}

    elif cmd == "ADJUST":
        # partner_id|week_start|amount|reference|ts
        partner_id = args[0].strip()
        week_start = args[1].strip()
        amount_str = args[2].strip()
        ref = args[3].strip() if len(args) > 3 else ""
        ts = args[4].strip() if len(args) > 4 else ""

        amount_paise = rupees_to_paise(amount_str)

        # Validation rules:
        # Reference is mandatory
        # Maximum adjustment = +-Rs 2,000 per partner per week
        rejection_reason = None
        if not ref:
            rejection_reason = "Missing mandatory reference"
        elif abs(amount_paise) > MAX_ADJUSTMENT_PAISE:
            rejection_reason = f"Adjustment amount {amount_str} exceeds limit of Rs 2000.00"

        status = "REJECTED" if rejection_reason else "ACCEPTED"
        cursor.execute("""
            INSERT INTO adjustments (partner_id, week_start, amount_paise, reference, adjustment_ts, status, rejection_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (partner_id, week_start, amount_paise, ref, ts, status, rejection_reason))

        return {
            "status": "SUCCESS" if status == "ACCEPTED" else "REJECTED",
            "cmd": cmd, "partner_id": partner_id, "amount": amount_str,
            "adjustment_status": status, "reason": rejection_reason
        }

    elif cmd == "SET_MARKETPLACE":
        # effective_date|flag
        effective_date = args[0].strip()
        flag_str = args[1].strip().lower()
        is_active = 1 if flag_str in ("true", "1", "yes") else 0
        cursor.execute("""
            INSERT INTO marketplace_periods (effective_date, is_active)
            VALUES (?, ?)
            ON CONFLICT(effective_date) DO UPDATE SET is_active = excluded.is_active
        """, (effective_date, is_active))
        return {"status": "SUCCESS", "cmd": cmd, "effective_date": effective_date, "is_active": bool(is_active)}

    elif cmd in ("PRINT_STATEMENT", "PRINT_BATCH", "PRINT_TDS_SUMMARY"):
        return {"status": "SUCCESS", "cmd": cmd, "args": args}

    return {"status": "UNKNOWN_COMMAND", "line": line}

def execute_command_script(conn: sqlite3.Connection, content: str) -> List[Dict[str, Any]]:
    """Execute multi-line commands.txt content in order."""
    results = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        res = execute_command_line(conn, line)
        results.append(res)
    return results
