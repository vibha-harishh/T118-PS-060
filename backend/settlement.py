"""Settlement batch processing engine with TDS, carry-forward, holds, and ledger accounting."""
import sqlite3
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from typing import Dict, Any, List, Optional

from backend.config import (
    MIN_PAYOUT_THRESHOLD_PAISE,
    BANK_RETRY_CHARGE_PAISE,
    MAX_BANK_RETRIES,
    paise_to_rupees,
    format_rupees,
    rupees_to_paise
)
from backend.calculations import (
    get_week_start_for_batch,
    get_batch_date_for_week
)
from backend.incentives import calculate_weekly_incentive
from backend.penalties import calculate_penalties, calculate_equipment_deduction
from backend.tds import calculate_tds
from backend.ledger import post_ledger_entry

def is_marketplace_active(conn: sqlite3.Connection, as_of_date: str) -> bool:
    """Check if marketplace mode (194-O) is active on or before as_of_date."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT is_active FROM marketplace_periods
        WHERE effective_date <= ?
        ORDER BY effective_date DESC LIMIT 1
    """, (as_of_date,))
    row = cursor.fetchone()
    return bool(row['is_active']) if row else False

def run_settlement_batch(conn: sqlite3.Connection, batch_date: str) -> Dict[str, Any]:
    """
    Execute Monday settlement batch for the previous Monday-to-Sunday week.
    Batch date is YYYY-MM-DD (must be a Monday).
    """
    cursor = conn.cursor()
    week_start = get_week_start_for_batch(batch_date)
    is_marketplace = is_marketplace_active(conn, batch_date)
    now_ts = f"{batch_date} 00:00:00"

    # Check if batch already processed
    cursor.execute("SELECT * FROM settlement_batches WHERE batch_date = ?", (batch_date,))
    if cursor.fetchone():
        raise ValueError(f"Batch {batch_date} has already been executed.")

    # Fetch all partners
    cursor.execute("SELECT * FROM partners ORDER BY partner_id ASC")
    partners = cursor.fetchall()

    batch_summary = {
        "batch_date": batch_date,
        "processed_ts": now_ts,
        "partners_paid": 0,
        "amount_paid_paise": 0,
        "partners_held": 0,
        "amount_held_paise": 0,
        "carried_forward_paise": 0,
        "retries": 0,
        "tds_total_paise": 0,
    }

    # Fetch retries count for this batch
    cursor.execute("""
        SELECT COUNT(*) as cnt FROM bank_returns WHERE batch_date = ?
    """, (batch_date,))
    retry_row = cursor.fetchone()
    batch_summary["retries"] = retry_row['cnt'] if retry_row else 0

    for partner in partners:
        p_id = partner['partner_id']

        # 1. Fetch task events for this partner in the previous Mon-Sun week
        cursor.execute("""
            SELECT event_type, rating, task_earnings_paise
            FROM task_events
            WHERE partner_id = ? AND week_start = ?
        """, (p_id, week_start))
        tasks = cursor.fetchall()

        completed = sum(1 for t in tasks if t['event_type'] == 'COMPLETED')
        cancelled_by_partner = sum(1 for t in tasks if t['event_type'] == 'CANCELLED_BY_PARTNER')
        cancelled_by_customer = sum(1 for t in tasks if t['event_type'] == 'CANCELLED_BY_CUSTOMER')
        total_tasks = completed + cancelled_by_partner + cancelled_by_customer

        # Ratings
        ratings = [t['rating'] for t in tasks if t['event_type'] == 'COMPLETED' and t['rating'] is not None]
        avg_rating = (Decimal(sum(ratings)) / Decimal(len(ratings))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if ratings else None
        avg_rating_float = float(avg_rating) if avg_rating is not None else 0.0

        # Cancellation rate pct
        if total_tasks > 0:
            cancellation_rate_pct = (Decimal(cancelled_by_partner) / Decimal(total_tasks) * Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            cancellation_rate_pct = Decimal('0.00')

        # Task earnings
        task_earnings_paise = sum(t['task_earnings_paise'] for t in tasks)

        # 2. Incentive calculation
        incentive_paise, _ = calculate_weekly_incentive(completed, cancellation_rate_pct, avg_rating)
        gross_paise = task_earnings_paise + incentive_paise

        # 3. Complaints
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM complaints
            WHERE partner_id = ? AND week_start = ?
        """, (p_id, week_start))
        complaints_count = cursor.fetchone()['cnt']

        # 4. Penalties and cap
        uncapped_penalties, penalty_cap_paise, applied_penalties_paise = calculate_penalties(
            cancelled_by_partner, complaints_count, gross_paise
        )

        # 5. Accepted Adjustments
        cursor.execute("""
            SELECT COALESCE(SUM(amount_paise), 0) as adj_total FROM adjustments
            WHERE partner_id = ? AND week_start = ? AND status = 'ACCEPTED'
        """, (p_id, week_start))
        adjustments_paise = cursor.fetchone()['adj_total']

        # 6. TDS Base: gross - applied_penalties + adjustments
        tds_base_paise = gross_paise - applied_penalties_paise + adjustments_paise

        # Cumulative FY payments before this batch
        cursor.execute("""
            SELECT COALESCE(SUM(tds_base_paise), 0) as prior_tds_base
            FROM weekly_statements
            WHERE partner_id = ? AND batch_date < ? AND status IN ('PAID', 'HELD_BANK', 'HELD_PAN', 'HELD_MANUAL', 'HELD')
        """, (p_id, batch_date))
        prior_settled_base = cursor.fetchone()['prior_tds_base']
        fy_cumulative_paise = partner['fy_paid_before_paise'] + prior_settled_base

        # 7. Check if any previous batches for this partner were HELD and are now ready for release
        # If partner bank was verified, or PAN updated, or manual hold released, previously held funds release!
        cursor.execute("""
            SELECT id, week_start, net_payable_paise, tds_base_paise, status
            FROM weekly_statements
            WHERE partner_id = ? AND status IN ('HELD_BANK', 'HELD_PAN', 'HELD_MANUAL', 'HELD')
        """, (p_id,))
        held_statements = cursor.fetchall()

        # Check partner's current hold statuses
        is_bank_unverified = (partner['bank_status'] == 'UNVERIFIED')
        is_held_manual = bool(partner['is_held_manual'])

        # 8. TDS calculation for this week
        # Notice: If partner was held over multiple weeks and released (e.g. EC-02 GP-004 & GP-005),
        # their release payment tests the single payment > 30k threshold!
        tds_section, tds_rate, tds_paise, is_missing_pan_hold = calculate_tds(
            partner_type=partner['partner_type'],
            category=partner['category'],
            pan_status=partner['pan_status'],
            tds_base_paise=tds_base_paise,
            fy_paid_cumulative_paise=fy_cumulative_paise,
            is_marketplace=is_marketplace
        )

        # 9. Equipment bag deduction
        cursor.execute("""
            SELECT COALESCE(SUM(equipment_deduction_paise), 0) as prior_deductions
            FROM weekly_statements
            WHERE partner_id = ? AND batch_date < ?
        """, (p_id, batch_date))
        prior_recovered = partner['equipment_recovered_before_paise'] + cursor.fetchone()['prior_deductions']
        net_before_tds_paise = gross_paise - applied_penalties_paise + adjustments_paise
        equipment_deduction_paise = calculate_equipment_deduction(prior_recovered, net_before_tds_paise)

        # 10. Carry-in from previous week
        # Look for previous week's statement
        cursor.execute("""
            SELECT status, net_payable_paise FROM weekly_statements
            WHERE partner_id = ?
            ORDER BY week_start DESC LIMIT 1
        """, (p_id,))
        prev_row = cursor.fetchone()
        carry_in_paise = 0
        had_carry_in = False
        if prev_row and prev_row['status'] == 'CARRIED_FORWARD':
            carry_in_paise = prev_row['net_payable_paise']
            had_carry_in = True

        # 11. Net payable calculation for current week
        net_payable_paise = tds_base_paise - tds_paise - equipment_deduction_paise + carry_in_paise

        # 12. Determine Status
        has_activity = (total_tasks > 0 or adjustments_paise != 0 or carry_in_paise > 0 or gross_paise > 0)

        if not has_activity:
            status = "NO_ACTIVITY"
            net_payable_paise = 0
        elif is_bank_unverified:
            status = "HELD_BANK"
        elif is_missing_pan_hold:
            status = "HELD_PAN"
        elif is_held_manual:
            status = "HELD_MANUAL"
        else:
            # Active and not held. Check minimum payout rule:
            # Minimum payout is Rs 200. Carry forward if below Rs 200 unless carried-forward from before
            if net_payable_paise < MIN_PAYOUT_THRESHOLD_PAISE and not had_carry_in:
                status = "CARRIED_FORWARD"
            else:
                status = "PAID"

        # Record weekly statement
        cursor.execute("""
            INSERT INTO weekly_statements (
                partner_id, week_start, batch_date, completed, cancelled_by_partner,
                cancelled_by_customer, cancellation_rate_pct, avg_rating,
                task_earnings_paise, incentive_paise, gross_paise, penalties_paise,
                penalty_cap_paise, adjustments_paise, tds_base_paise, tds_section,
                tds_rate_pct, tds_paise, equipment_deduction_paise, carry_in_paise,
                net_payable_paise, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p_id, week_start, batch_date, completed, cancelled_by_partner,
            cancelled_by_customer, float(cancellation_rate_pct), avg_rating_float,
            task_earnings_paise, incentive_paise, gross_paise, applied_penalties_paise,
            penalty_cap_paise, adjustments_paise, tds_base_paise, tds_section,
            float(tds_rate * 100), tds_paise, equipment_deduction_paise, carry_in_paise,
            net_payable_paise, status
        ))

        # Handle release of previously held statements if partner is now unheld!
        release_amount_paise = 0
        if status == "PAID" and held_statements:
            for hs in held_statements:
                release_amount_paise += hs['net_payable_paise']
                cursor.execute("""
                    UPDATE weekly_statements SET status = 'PAID' WHERE id = ?
                """, (hs['id'],))
                # Post release in ledger
                post_ledger_entry(
                    conn=conn,
                    partner_id=p_id,
                    entry_ts=now_ts,
                    entry_type="HELD_RELEASE",
                    week_start=hs['week_start'],
                    amount_paise=hs['net_payable_paise'],
                    paid_delta_paise=hs['net_payable_paise']
                )

        # Post ledger movements for current week
        if status == "PAID":
            # Task Earnings
            if task_earnings_paise > 0:
                post_ledger_entry(
                    conn=conn, partner_id=p_id, entry_ts=now_ts, entry_type="EARNING",
                    week_start=week_start, amount_paise=task_earnings_paise,
                    earned_delta_paise=task_earnings_paise
                )
            # Incentive
            if incentive_paise > 0:
                post_ledger_entry(
                    conn=conn, partner_id=p_id, entry_ts=now_ts, entry_type="INCENTIVE",
                    week_start=week_start, amount_paise=incentive_paise,
                    earned_delta_paise=incentive_paise
                )
            # Penalties
            if applied_penalties_paise > 0:
                post_ledger_entry(
                    conn=conn, partner_id=p_id, entry_ts=now_ts, entry_type="PENALTY",
                    week_start=week_start, amount_paise=-applied_penalties_paise
                )
            # Adjustments
            if adjustments_paise != 0:
                post_ledger_entry(
                    conn=conn, partner_id=p_id, entry_ts=now_ts, entry_type="ADJUSTMENT",
                    week_start=week_start, amount_paise=adjustments_paise,
                    earned_delta_paise=max(0, adjustments_paise)
                )
            # TDS
            if tds_paise > 0:
                post_ledger_entry(
                    conn=conn, partner_id=p_id, entry_ts=now_ts, entry_type="TDS",
                    week_start=week_start, amount_paise=-tds_paise,
                    withheld_delta_paise=tds_paise
                )
            # Equipment recovery
            if equipment_deduction_paise > 0:
                post_ledger_entry(
                    conn=conn, partner_id=p_id, entry_ts=now_ts, entry_type="EQUIPMENT_RECOVERY",
                    week_start=week_start, amount_paise=-equipment_deduction_paise,
                    recovered_delta_paise=equipment_deduction_paise
                )
            # Payout
            total_payout_this_batch = net_payable_paise + release_amount_paise
            if total_payout_this_batch > 0:
                post_ledger_entry(
                    conn=conn, partner_id=p_id, entry_ts=now_ts, entry_type="PAYOUT",
                    week_start=week_start, amount_paise=-total_payout_this_batch,
                    paid_delta_paise=net_payable_paise
                )

            batch_summary["partners_paid"] += 1
            batch_summary["amount_paid_paise"] += total_payout_this_batch
            batch_summary["tds_total_paise"] += tds_paise

        elif status in ("HELD_BANK", "HELD_PAN", "HELD_MANUAL"):
            batch_summary["partners_held"] += 1
            batch_summary["amount_held_paise"] += net_payable_paise
            batch_summary["tds_total_paise"] += tds_paise
            # Post accrual in ledger
            if task_earnings_paise > 0:
                post_ledger_entry(
                    conn=conn, partner_id=p_id, entry_ts=now_ts, entry_type="EARNING",
                    week_start=week_start, amount_paise=task_earnings_paise,
                    earned_delta_paise=task_earnings_paise
                )
            if incentive_paise > 0:
                post_ledger_entry(
                    conn=conn, partner_id=p_id, entry_ts=now_ts, entry_type="INCENTIVE",
                    week_start=week_start, amount_paise=incentive_paise,
                    earned_delta_paise=incentive_paise
                )
            if tds_paise > 0:
                post_ledger_entry(
                    conn=conn, partner_id=p_id, entry_ts=now_ts, entry_type="TDS",
                    week_start=week_start, amount_paise=-tds_paise,
                    withheld_delta_paise=tds_paise
                )

        elif status == "CARRIED_FORWARD":
            batch_summary["carried_forward_paise"] += net_payable_paise
            if task_earnings_paise > 0:
                post_ledger_entry(
                    conn=conn, partner_id=p_id, entry_ts=now_ts, entry_type="EARNING",
                    week_start=week_start, amount_paise=task_earnings_paise,
                    earned_delta_paise=task_earnings_paise
                )

    # Save settlement batch summary
    cursor.execute("""
        INSERT INTO settlement_batches (
            batch_date, processed_ts, partners_paid, amount_paid_paise,
            partners_held, amount_held_paise, carried_forward_paise,
            retries, tds_total_paise
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        batch_summary["batch_date"],
        batch_summary["processed_ts"],
        batch_summary["partners_paid"],
        batch_summary["amount_paid_paise"],
        batch_summary["partners_held"],
        batch_summary["amount_held_paise"],
        batch_summary["carried_forward_paise"],
        batch_summary["retries"],
        batch_summary["tds_total_paise"]
    ))

    return batch_summary
