"""Partner Ledger module maintaining running financial entries."""
import sqlite3
from decimal import Decimal
from typing import Optional, List, Dict, Any

from backend.config import paise_to_rupees, format_rupees

def post_ledger_entry(
    conn: sqlite3.Connection,
    partner_id: str,
    entry_ts: str,
    entry_type: str,
    week_start: Optional[str],
    amount_paise: int,
    earned_delta_paise: int = 0,
    withheld_delta_paise: int = 0,
    paid_delta_paise: int = 0,
    recovered_delta_paise: int = 0
) -> int:
    """Post an immutable entry to the partner's running ledger."""
    cursor = conn.cursor()
    # Get last running balances for partner
    cursor.execute("""
        SELECT earned_to_date_paise, withheld_to_date_paise, paid_to_date_paise, recovered_to_date_paise
        FROM ledger_entries
        WHERE partner_id = ?
        ORDER BY id DESC LIMIT 1
    """, (partner_id,))
    row = cursor.fetchone()

    if row:
        earned_to_date = row['earned_to_date_paise'] + earned_delta_paise
        withheld_to_date = row['withheld_to_date_paise'] + withheld_delta_paise
        paid_to_date = row['paid_to_date_paise'] + paid_delta_paise
        recovered_to_date = row['recovered_to_date_paise'] + recovered_delta_paise
    else:
        # Initial partner balances from partners table (FY prior amounts)
        cursor.execute("""
            SELECT fy_paid_before_paise, fy_tds_before_paise, equipment_recovered_before_paise
            FROM partners WHERE partner_id = ?
        """, (partner_id,))
        prow = cursor.fetchone()
        
        base_earned = 0
        base_paid = prow['fy_paid_before_paise'] if prow else 0
        base_withheld = prow['fy_tds_before_paise'] if prow else 0
        base_recovered = prow['equipment_recovered_before_paise'] if prow else 0

        earned_to_date = base_earned + earned_delta_paise
        withheld_to_date = base_withheld + withheld_delta_paise
        paid_to_date = base_paid + paid_delta_paise
        recovered_to_date = base_recovered + recovered_delta_paise

    cursor.execute("""
        INSERT INTO ledger_entries (
            partner_id, entry_ts, entry_type, week_start, amount_paise,
            earned_to_date_paise, withheld_to_date_paise, paid_to_date_paise, recovered_to_date_paise
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        partner_id, entry_ts, entry_type, week_start, amount_paise,
        earned_to_date, withheld_to_date, paid_to_date, recovered_to_date
    ))
    return cursor.lastrowid
