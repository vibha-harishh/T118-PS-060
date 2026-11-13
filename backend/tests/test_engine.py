
"""Comprehensive unit and integration test suite for Gig-Worker Payout Engine edge cases."""

import unittest
import os
import sqlite3
from decimal import Decimal
import tempfile

TEST_DB_FILE = "/tmp/test_payout_engine.db"
os.environ["SQLITE_DB_PATH"] = TEST_DB_FILE

from backend.config import (
    rupees_to_paise,
    paise_to_rupees,
    format_rupees,
    MIN_PAYOUT_THRESHOLD_PAISE
)
from backend.db import init_db, get_db_connection
from backend.calculations import calculate_task_earning, get_week_start
from backend.incentives import calculate_weekly_incentive
from backend.penalties import calculate_penalties, calculate_equipment_deduction
from backend.tds import calculate_tds
from backend.partners import register_partner, validate_pan
from backend.settlement import run_settlement_batch
from backend.commands import execute_command_line


class TestPayoutEngineEdgeCases(unittest.TestCase):

    def setUp(self):
        init_db(drop_all=True)
        self.conn = get_db_connection()

    def tearDown(self):
        self.conn.close()

    def test_ec01_exactly_60_tasks_and_exactly_8_percent_cancellation(self):
        """EC-01: Exactly 60 completed + 6 partner cancel + 9 customer cancel = 8%."""
        completed = 60
        cancelled_partner = 6
        cancelled_cust = 9
        total = completed + cancelled_partner + cancelled_cust

        cancellation_rate_pct = (
            Decimal(cancelled_partner) / Decimal(total) * Decimal('100')
        )
        self.assertEqual(cancellation_rate_pct, Decimal('8.00'))

        incentive_paise, reason = calculate_weekly_incentive(
            completed_count=completed,
            cancellation_rate_pct=cancellation_rate_pct,
            avg_rating=Decimal('4.5')
        )
        self.assertEqual(incentive_paise, 60000)
        self.assertEqual(reason, "Eligible")

        uncapped, cap, applied = calculate_penalties(
            partner_cancellations=cancelled_partner,
            complaints_count=0,
            gross_paise=200000
        )
        self.assertEqual(uncapped, 15000)
        self.assertEqual(applied, 15000)

    def test_ec02_single_payment_30000_vs_30001_under_194c(self):
        """EC-02: Exactly Rs 30,000 does not cross 194C; Rs 30,001 does."""
        base_30k = rupees_to_paise('30000.00')

        sec1, rate1, tds1, _ = calculate_tds(
            partner_type="FIRM",
            category="DELIVERY",
            pan_status="VALID",
            tds_base_paise=base_30k,
            fy_paid_cumulative_paise=0,
            is_marketplace=False
        )
        self.assertEqual(rate1, Decimal('0.0'))
        self.assertEqual(tds1, 0)

        base_30001 = rupees_to_paise('30001.00')

        sec2, rate2, tds2, _ = calculate_tds(
            partner_type="FIRM",
            category="DELIVERY",
            pan_status="VALID",
            tds_base_paise=base_30001,
            fy_paid_cumulative_paise=0,
            is_marketplace=False
        )
        self.assertEqual(sec2, "194C")
        self.assertEqual(rate2, Decimal('0.02'))
        self.assertEqual(
            tds2,
            int(Decimal(base_30001) * Decimal('0.02'))
        )

    def test_ec03_cumulative_194c_crossed_by_500_payment(self):
        """EC-03: Rs 99,800 + Rs 500 crosses the Rs 1 lakh threshold."""
        prior_cumulative = rupees_to_paise('99800.00')
        current_base = rupees_to_paise('500.00')

        sec, rate, tds, _ = calculate_tds(
            partner_type="INDIVIDUAL",
            category="DELIVERY",
            pan_status="VALID",
            tds_base_paise=current_base,
            fy_paid_cumulative_paise=prior_cumulative,
            is_marketplace=False
        )

        self.assertEqual(sec, "194C")
        self.assertEqual(rate, Decimal('0.01'))
        self.assertEqual(tds, 500)

    def test_ec04_penalty_cap_20_percent_binding(self):
        """EC-04: Penalties are capped at 20% of weekly gross."""
        gross_paise = rupees_to_paise('1225.00')

        uncapped, cap, applied = calculate_penalties(
            partner_cancellations=4,
            complaints_count=1,
            gross_paise=gross_paise
        )

        self.assertEqual(uncapped, 25000)
        self.assertEqual(cap, 24500)
        self.assertEqual(applied, 24500)

    def test_ec05_minimum_payout_199_50_carried_forward(self):
        """EC-05: Exact Rs 199.50 carries forward and is paid next week."""
        register_partner(
            conn=self.conn,
            partner_id="GP-EC05",
            partner_name="EC05 Test Partner",
            partner_type="INDIVIDUAL",
            category="DELIVERY",
            pan_status="VALID",
            pan="ABCDE1234F",
            bank_status="VERIFIED",
            ifsc="HDFC0001234",
            city="Bengaluru",
            onboarding_date="2026-01-01"
        )

        self.conn.execute("""
            INSERT INTO adjustments (
                partner_id, week_start, amount_paise,
                reference, adjustment_ts, status
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "GP-EC05",
            "2026-09-07",
            19950,
            "EC05-19950",
            "2026-09-13 12:00:00",
            "ACCEPTED"
        ))

        run_settlement_batch(self.conn, "2026-09-14")

        first = self.conn.execute("""
            SELECT net_payable_paise, status
            FROM weekly_statements
            WHERE partner_id = ? AND week_start = ?
        """, ("GP-EC05", "2026-09-07")).fetchone()

        self.assertEqual(first["net_payable_paise"], 19950)
        self.assertEqual(first["status"], "CARRIED_FORWARD")

        run_settlement_batch(self.conn, "2026-09-21")

        second = self.conn.execute("""
            SELECT carry_in_paise, net_payable_paise, status
            FROM weekly_statements
            WHERE partner_id = ? AND week_start = ?
        """, ("GP-EC05", "2026-09-14")).fetchone()

        self.assertEqual(second["carry_in_paise"], 19950)
        self.assertEqual(second["net_payable_paise"], 19950)
        self.assertEqual(second["status"], "PAID")

    def test_positive_adjustment_increases_tds_base(self):
        """A positive adjustment increases the TDS base and TDS deducted."""
        register_partner(
            conn=self.conn,
            partner_id="GP-POS-ADJ",
            partner_name="Positive Adjustment Test",
            partner_type="INDIVIDUAL",
            category="DELIVERY",
            pan_status="VALID",
            pan="ABCDE1234F",
            bank_status="VERIFIED",
            ifsc="HDFC0001234",
            city="Bengaluru",
            onboarding_date="2026-01-01",
            fy_paid_before=99500.0
        )

        self.conn.execute("""
            INSERT INTO adjustments (
                partner_id, week_start, amount_paise,
                reference, adjustment_ts, status
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "GP-POS-ADJ",
            "2026-09-07",
            100000,
            "POS-ADJ-TEST",
            "2026-09-13 12:00:00",
            "ACCEPTED"
        ))

        run_settlement_batch(self.conn, "2026-09-14")

        statement = self.conn.execute("""
            SELECT adjustments_paise, tds_base_paise,
                   tds_section, tds_rate_pct, tds_paise, status
            FROM weekly_statements
            WHERE partner_id = ? AND week_start = ?
        """, ("GP-POS-ADJ", "2026-09-07")).fetchone()

        self.assertEqual(statement["adjustments_paise"], 100000)
        self.assertEqual(statement["tds_base_paise"], 100000)
        self.assertEqual(statement["tds_section"], "194C")
        self.assertEqual(statement["tds_rate_pct"], 1.0)
        self.assertEqual(statement["tds_paise"], 1000)
        self.assertEqual(statement["status"], "PAID")

    def test_ec06_bank_return_retry_charges_and_exhaustion(self):
        """EC-06: Third bank return exhausts two retries."""
        register_partner(
            conn=self.conn,
            partner_id="GP-TEST-01",
            partner_name="Test Partner",
            partner_type="INDIVIDUAL",
            category="DELIVERY",
            pan_status="VALID",
            pan="ABCDE1234F",
            bank_status="VERIFIED",
            ifsc="HDFC0001234",
            city="Bengaluru",
            onboarding_date="2026-01-01"
        )

        res1 = execute_command_line(
            self.conn,
            "BANK_RETURN|GP-TEST-01|2026-09-14|2026-09-16 12:00:00|ACCOUNT_CLOSED"
        )
        self.assertEqual(res1["retry_number"], 1)
        self.assertFalse(res1["held_manual"])

        res2 = execute_command_line(
            self.conn,
            "BANK_RETURN|GP-TEST-01|2026-09-21|2026-09-23 12:00:00|ACCOUNT_CLOSED"
        )
        self.assertEqual(res2["retry_number"], 2)
        self.assertFalse(res2["held_manual"])

        res3 = execute_command_line(
            self.conn,
            "BANK_RETURN|GP-TEST-01|2026-09-28|2026-09-30 12:00:00|ACCOUNT_CLOSED"
        )
        self.assertEqual(res3["retry_number"], 3)
        self.assertTrue(res3["held_manual"])

    def test_ec07_pan_missing_cumulative_threshold_hold(self):
        """EC-07: Missing PAN above Rs 50,000 triggers a hold."""
        prior = rupees_to_paise('49000.00')
        current = rupees_to_paise('2000.00')

        sec, rate, tds, is_hold = calculate_tds(
            partner_type="INDIVIDUAL",
            category="DELIVERY",
            pan_status="MISSING",
            tds_base_paise=current,
            fy_paid_cumulative_paise=prior,
            is_marketplace=False
        )

        self.assertTrue(is_hold)
        self.assertEqual(rate, Decimal('0.20'))

    def test_ec08_marketplace_flag_and_thresholds(self):
        """EC-08: Marketplace 194-O threshold rules."""
        sec1, rate1, tds1, _ = calculate_tds(
            partner_type="INDIVIDUAL",
            category="DELIVERY",
            pan_status="VALID",
            tds_base_paise=rupees_to_paise('5000.00'),
            fy_paid_cumulative_paise=rupees_to_paise('100000.00'),
            is_marketplace=True
        )

        self.assertEqual(sec1, "NONE")
        self.assertEqual(tds1, 0)

        sec2, rate2, tds2, _ = calculate_tds(
            partner_type="FIRM",
            category="DELIVERY",
            pan_status="VALID",
            tds_base_paise=rupees_to_paise('5000.00'),
            fy_paid_cumulative_paise=rupees_to_paise('10000.00'),
            is_marketplace=True
        )

        self.assertEqual(sec2, "194-O")
        self.assertEqual(rate2, Decimal('0.01'))
        self.assertEqual(tds2, 5000)

    def test_invalid_pan_tds_20_percent(self):
        """Invalid PAN attracts 20% TDS after applicable thresholds."""

        sec1, rate1, tds1, hold1 = calculate_tds(
            partner_type="INDIVIDUAL",
            category="DELIVERY",
            pan_status="INVALID",
            tds_base_paise=rupees_to_paise("31000.00"),
            fy_paid_cumulative_paise=0,
            is_marketplace=False
        )

        self.assertEqual(sec1, "194C")
        self.assertEqual(rate1, Decimal("0.20"))
        self.assertEqual(tds1, 620000)
        self.assertFalse(hold1)

        sec2, rate2, tds2, hold2 = calculate_tds(
            partner_type="INDIVIDUAL",
            category="SERVICE_PROFESSIONAL",
            pan_status="INVALID",
            tds_base_paise=rupees_to_paise("1000.00"),
            fy_paid_cumulative_paise=rupees_to_paise("30000.00"),
            is_marketplace=False
        )

        self.assertEqual(sec2, "194J")
        self.assertEqual(rate2, Decimal("0.20"))
        self.assertEqual(tds2, 20000)
        self.assertFalse(hold2)

    def test_manual_adjustment_validation(self):
        """Adjustments above Rs 2000 or without references are rejected."""
        register_partner(
            conn=self.conn,
            partner_id="GP-TEST-02",
            partner_name="Test Adj",
            partner_type="INDIVIDUAL",
            category="DELIVERY",
            pan_status="VALID",
            pan="ABCDE1234F",
            bank_status="VERIFIED",
            ifsc="HDFC0001234",
            city="Bengaluru",
            onboarding_date="2026-01-01"
        )

        res1 = execute_command_line(
            self.conn,
            "ADJUST|GP-TEST-02|2026-10-05|2500.00|TKT-88213|2026-10-08 11:00:00"
        )
        self.assertEqual(res1["status"], "REJECTED")

        res2 = execute_command_line(
            self.conn,
            "ADJUST|GP-TEST-02|2026-10-05|-350.00||2026-10-08 12:00:00"
        )
        self.assertEqual(res2["status"], "REJECTED")

        res3 = execute_command_line(
            self.conn,
            "ADJUST|GP-TEST-02|2026-10-05|-350.00|TKT-88219|2026-10-08 13:00:00"
        )
        self.assertEqual(res3["status"], "SUCCESS")

    def test_equipment_deduction_limit_and_pause(self):
        """Recovery stops at Rs 1800 and pauses below Rs 1000."""
        deduct1 = calculate_equipment_deduction(
            equipment_already_recovered_paise=rupees_to_paise('1650.00'),
            net_before_tds_paise=rupees_to_paise('1500.00')
        )
        self.assertEqual(deduct1, 15000)

        deduct2 = calculate_equipment_deduction(
            equipment_already_recovered_paise=rupees_to_paise('1800.00'),
            net_before_tds_paise=rupees_to_paise('1500.00')
        )
        self.assertEqual(deduct2, 0)

        deduct3 = calculate_equipment_deduction(
            equipment_already_recovered_paise=rupees_to_paise('500.00'),
            net_before_tds_paise=rupees_to_paise('800.00')
        )
        self.assertEqual(deduct3, 0)

    def test_equipment_deduction_in_weekly_settlement(self):
        """Settlement deducts the remaining Rs 150 when payable exceeds Rs 1000."""
        register_partner(
            conn=self.conn,
            partner_id="GP-EQUIP-TEST",
            partner_name="Equipment Test Partner",
            partner_type="INDIVIDUAL",
            category="DELIVERY",
            pan_status="VALID",
            pan="ABCDE1234F",
            bank_status="VERIFIED",
            ifsc="HDFC0001234",
            city="Bengaluru",
            onboarding_date="2026-01-01",
            equipment_recovered_before=1650.0
        )

        self.conn.execute("""
            INSERT INTO adjustments (
                partner_id, week_start, amount_paise,
                reference, adjustment_ts, status
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "GP-EQUIP-TEST",
            "2026-09-07",
            120000,
            "EQUIP-TEST-REF",
            "2026-09-13 12:00:00",
            "ACCEPTED"
        ))

        run_settlement_batch(self.conn, "2026-09-14")

        result = self.conn.execute("""
            SELECT equipment_deduction_paise, net_payable_paise, status
            FROM weekly_statements
            WHERE partner_id = ? AND week_start = ?
        """, ("GP-EQUIP-TEST", "2026-09-07")).fetchone()

        self.assertEqual(result["equipment_deduction_paise"], 15000)
        self.assertEqual(result["net_payable_paise"], 105000)
        self.assertEqual(result["status"], "PAID")

    def test_timestamp_attribution_sunday_vs_monday(self):
        """Sunday 23:59:59 belongs to previous week; Monday belongs to current week."""
        sun_ts = "2026-09-20 23:59:59"
        mon_ts = "2026-10-05 00:00:10"

        self.assertEqual(get_week_start(sun_ts), "2026-09-14")
        self.assertEqual(get_week_start(mon_ts), "2026-10-05")


if __name__ == "__main__":
    unittest.main()
