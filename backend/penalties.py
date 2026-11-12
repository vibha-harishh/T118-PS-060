"""Penalties and equipment deductions module."""
from decimal import Decimal, ROUND_HALF_UP
from typing import Tuple

from backend.config import (
    FREE_PARTNER_CANCELLATIONS,
    PENALTY_PER_EXTRA_CANCEL_PAISE,
    COMPLAINT_PENALTY_PAISE,
    PENALTY_CAP_RATIO,
    EQUIPMENT_WEEKLY_DEDUCTION_PAISE,
    EQUIPMENT_MAX_RECOVERY_PAISE,
    EQUIPMENT_PAUSE_THRESHOLD_PAISE
)

def calculate_penalties(
    partner_cancellations: int,
    complaints_count: int,
    gross_paise: int
) -> Tuple[int, int, int]:
    """
    Calculate uncapped penalties, penalty cap (20% of gross), and applied penalties.
    Returns:
    (uncapped_penalties_paise, penalty_cap_paise, applied_penalties_paise)
    """
    # Cancellation penalty: First 3 free, +Rs 50 each thereafter
    extra_cancels = max(0, partner_cancellations - FREE_PARTNER_CANCELLATIONS)
    cancel_penalty_paise = extra_cancels * PENALTY_PER_EXTRA_CANCEL_PAISE

    # Complaint penalty: Rs 200 per verified complaint
    complaint_penalty_paise = complaints_count * COMPLAINT_PENALTY_PAISE

    uncapped_penalties = cancel_penalty_paise + complaint_penalty_paise

    # 20% penalty cap on gross earnings
    # Note: 20% of gross. Using Decimal rounding
    gross_dec = Decimal(gross_paise)
    cap_dec = (gross_dec * PENALTY_CAP_RATIO).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    penalty_cap_paise = int(cap_dec)

    applied_penalties = min(uncapped_penalties, penalty_cap_paise)

    return uncapped_penalties, penalty_cap_paise, applied_penalties

def calculate_equipment_deduction(
    equipment_already_recovered_paise: int,
    net_before_tds_paise: int
) -> int:
    """
    Calculate equipment bag deduction for the week in paise.
    Rules:
    - Rs 150 per week
    - Max lifetime recovery = Rs 1,800
    - Pause deduction if net payable before TDS is below Rs 1,000
    """
    remaining_recovery = max(0, EQUIPMENT_MAX_RECOVERY_PAISE - equipment_already_recovered_paise)
    if remaining_recovery == 0:
        return 0

    # Pause deduction if net before TDS is below Rs 1000
    if net_before_tds_paise < EQUIPMENT_PAUSE_THRESHOLD_PAISE:
        return 0

    return min(EQUIPMENT_WEEKLY_DEDUCTION_PAISE, remaining_recovery)
