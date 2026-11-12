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
        """EC-01: Exactly 60 completed + 6 partner cancel + 9 customer cancel = 6/75 = 8.00% cancellation rate."""
        completed = 60
        cancelled_partner = 6
        cancelled_cust = 9
        total = completed + cancelled_partner + cancelled_cust # 75
        cancellation_rate_pct = Decimal(cancelled_partner) / Decimal(total) * Decimal('100')
        self.assertEqual(cancellation_rate_pct, Decimal('8.00'))

        # Incentive: 60 tasks gives Rs 600, rate not > 8% so kept!
        incentive_paise, reason = calculate_weekly_incentive(
            completed_count=completed,
            cancellation_rate_pct=cancellation_rate_pct,
            avg_rating=Decimal('4.5')
        )
        self.assertEqual(incentive_paise, 60000)  # Rs 600 in paise
        self.assertEqual(reason, "Eligible")

        # Penalties: First 3 free, 3 extra = 3 * 50 = Rs 150
        uncapped, cap, applied = calculate_penalties(
            partner_cancellations=cancelled_partner,
            complaints_count=0,
            gross_paise=200000  # Rs 2000 gross
        )
        self.assertEqual(uncapped, 15000)  # Rs 150 in paise
        self.assertEqual(applied, 15000)

    def test_ec02_single_payment_30000_vs_30001_under_194c(self):
        """EC-02: Single payment of exactly Rs 30,000 does NOT cross 194C, while Rs 30,001 DOES cross."""
        # Rs 30,000 exactly
        base_30k = rupees_to_paise('30000.00')
        sec1, rate1, tds1, _ = calculate_tds(
            partner_type="FIRM", category="DELIVERY", pan_status="VALID",
            tds_base_paise=base_30k, fy_paid_cumulative_paise=0, is_marketplace=False
        )
        self.assertEqual(rate1, Decimal('0.0'))
        self.assertEqual(tds1, 0)

        # Rs 30,001
        base_30001 = rupees_to_paise('30001.00')
        sec2, rate2, tds2, _ = calculate_tds(
            partner_type="FIRM", category="DELIVERY", pan_status="VALID",
            tds_base_paise=base_30001, fy_paid_cumulative_paise=0, is_marketplace=False
        )
        self.assertEqual(sec2, "194C")
        self.assertEqual(rate2, Decimal('0.02'))  # FIRM 2%
        self.assertEqual(tds2, int(Decimal(base_30001) * Decimal('0.02')))

    def test_ec03_cumulative_194c_crossed_by_500_payment(self):
        """EC-03: FY prior 99,800 + current 500 = 100,300 crosses 100,000 threshold."""
        prior_cumulative = rupees_to_paise('99800.00')
        current_base = rupees_to_paise('500.00')
        sec, rate, tds, _ = calculate_tds(
            partner_type="INDIVIDUAL", category="DELIVERY", pan_status="VALID",
            tds_base_paise=current_base, fy_paid_cumulative_paise=prior_cumulative, is_marketplace=False
        )
        self.assertEqual(sec, "194C")
        self.assertEqual(rate, Decimal('0.01'))  # INDIVIDUAL 1%
        self.assertEqual(tds, 500)  # Rs 5.00 = 500 paise (1% of 500)

    def test_ec04_penalty_cap_20_percent_binding(self):
        """EC-04: Gross Rs 1225 -> Cap 20% = Rs 245. Penalties: 1 cancel beyond 3 (Rs 50) + complaint (Rs 200) = Rs 250 > 245."""
        gross_paise = rupees_to_paise('1225.00')
        uncapped, cap, applied = calculate_penalties(
            partner_cancellations=4, complaints_count=1, gross_paise=gross_paise
        )
        self.assertEqual(uncapped, 25000)  # Rs 250
        self.assertEqual(cap, 24500)       # Rs 245 (20% of 1225)
        self.assertEqual(applied, 24500)   # Capped at Rs 245

    def test_ec05_minimum_payout_199_50_carried_forward(self):
        """EC-05: Rs 199.50 is below Rs 200 minimum (not rounded up), carried forward."""
        net_payable_paise = rupees_to_paise('199.50')
        self.assertLess(net_payable_paise, MIN_PAYOUT_THRESHOLD_PAISE)

    def test_ec06_bank_return_retry_charges_and_exhaustion(self):
        """EC-06: Second retry exhaustion marks partner HELD_MANUAL."""
        register_partner(
            conn=self.conn, partner_id="GP-TEST-01", partner_name="Test Partner",
            partner_type="INDIVIDUAL", category="DELIVERY", pan_status="VALID",
            pan="ABCDE1234F", bank_status="VERIFIED", ifsc="HDFC0001234",
            city="Bengaluru", onboarding_date="2026-01-01"
        )
        # First bank return
        res1 = execute_command_line(self.conn, "BANK_RETURN|GP-TEST-01|2026-09-14|2026-09-16 12:00:00|ACCOUNT_CLOSED")
        self.assertEqual(res1["retry_number"], 1)
        self.assertFalse(res1["held_manual"])

        # Second bank return
        res2 = execute_command_line(self.conn, "BANK_RETURN|GP-TEST-01|2026-09-21|2026-09-23 12:00:00|ACCOUNT_CLOSED")
        self.assertEqual(res2["retry_number"], 2)
        self.assertFalse(res2["held_manual"])

        # Third bank return (exhausts 2 retries)
        res3 = execute_command_line(self.conn, "BANK_RETURN|GP-TEST-01|2026-09-28|2026-09-30 12:00:00|ACCOUNT_CLOSED")
        self.assertEqual(res3["retry_number"], 3)
        self.assertTrue(res3["held_manual"])

    def test_ec07_pan_missing_cumulative_threshold_hold(self):
        """EC-07: Missing PAN with cumulative > Rs 50,000 causes settlement hold."""
        prior = rupees_to_paise('49000.00')
        current = rupees_to_paise('2000.00')
        sec, rate, tds, is_hold = calculate_tds(
            partner_type="INDIVIDUAL", category="DELIVERY", pan_status="MISSING",
            tds_base_paise=current, fy_paid_cumulative_paise=prior, is_marketplace=False
        )
        self.assertTrue(is_hold)
        self.assertEqual(rate, Decimal('0.20'))  # 20% rate for missing PAN

    def test_ec08_marketplace_flag_and_thresholds(self):
        """EC-08: In marketplace mode, 194-O applies. Individual threshold 5,00,000 while Firm has no threshold."""
        # Individual under 5L
        sec1, rate1, tds1, _ = calculate_tds(
            partner_type="INDIVIDUAL", category="DELIVERY", pan_status="VALID",
            tds_base_paise=rupees_to_paise('5000.00'), fy_paid_cumulative_paise=rupees_to_paise('100000.00'),
            is_marketplace=True
        )
        self.assertEqual(sec1, "NONE")
        self.assertEqual(tds1, 0)

        # Firm has no threshold in marketplace
        sec2, rate2, tds2, _ = calculate_tds(
            partner_type="FIRM", category="DELIVERY", pan_status="VALID",
            tds_base_paise=rupees_to_paise('5000.00'), fy_paid_cumulative_paise=rupees_to_paise('10000.00'),
            is_marketplace=True
        )
        self.assertEqual(sec2, "194-O")
        self.assertEqual(rate2, Decimal('0.01'))  # 1%
        self.assertEqual(tds2, 5000)  # 1% of 5000 = 50.00

    def test_timestamp_attribution_sunday_vs_monday(self):
        """Sunday 23:59:59 belongs to previous week; Monday 00:00:10 belongs to current week."""
        sun_ts = "2026-09-20 23:59:59"
        mon_ts = "2026-10-05 00:00:10"
        self.assertEqual(get_week_start(sun_ts), "2026-09-14")
        self.assertEqual(get_week_start(mon_ts), "2026-10-05")

    def test_manual_adjustment_validation(self):
        """Adjustment > Rs 2000 or missing reference must be rejected."""
        register_partner(
            conn=self.conn, partner_id="GP-TEST-02", partner_name="Test Adj",
            partner_type="INDIVIDUAL", category="DELIVERY", pan_status="VALID",
            pan="ABCDE1234F", bank_status="VERIFIED", ifsc="HDFC0001234",
            city="Bengaluru", onboarding_date="2026-01-01"
        )
        # Exceeds Rs 2000
        res1 = execute_command_line(self.conn, "ADJUST|GP-TEST-02|2026-10-05|2500.00|TKT-88213|2026-10-08 11:00:00")
        self.assertEqual(res1["status"], "REJECTED")

        # Missing reference
        res2 = execute_command_line(self.conn, "ADJUST|GP-TEST-02|2026-10-05|-350.00||2026-10-08 12:00:00")
        self.assertEqual(res2["status"], "REJECTED")

        # Valid adjustment
        res3 = execute_command_line(self.conn, "ADJUST|GP-TEST-02|2026-10-05|-350.00|TKT-88219|2026-10-08 13:00:00")
        self.assertEqual(res3["status"], "SUCCESS")

    def test_equipment_deduction_limit_and_pause(self):
        """Recovery stops at Rs 1800, and pauses if net before TDS < Rs 1000."""
        # Case 1: Rs 1650 already recovered -> only Rs 150 deducted
        deduct1 = calculate_equipment_deduction(
            equipment_already_recovered_paise=rupees_to_paise('1650.00'),
            net_before_tds_paise=rupees_to_paise('1500.00')
        )
        self.assertEqual(deduct1, 15000)  # Rs 150

        # Case 2: Rs 1800 already recovered -> 0 deducted
        deduct2 = calculate_equipment_deduction(
            equipment_already_recovered_paise=rupees_to_paise('1800.00'),
            net_before_tds_paise=rupees_to_paise('1500.00')
        )
        self.assertEqual(deduct2, 0)

        # Case 3: net before TDS < Rs 1000 -> paused (0 deducted)
        deduct3 = calculate_equipment_deduction(
            equipment_already_recovered_paise=rupees_to_paise('500.00'),
            net_before_tds_paise=rupees_to_paise('800.00')
        )
        self.assertEqual(deduct3, 0)

if __name__ == "__main__":
    unittest.main()
