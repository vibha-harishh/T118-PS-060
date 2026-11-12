"""TDS Calculation Module implementing 194C, 194J, 194-O and PAN rules."""
from decimal import Decimal, ROUND_HALF_UP
from typing import Tuple

from backend.config import (
    THRESHOLD_194C_SINGLE_PAISE,
    THRESHOLD_194C_ANNUAL_PAISE,
    RATE_194C_INDIVIDUAL,
    RATE_194C_FIRM,
    THRESHOLD_194J_ANNUAL_PAISE,
    RATE_194J,
    THRESHOLD_194O_INDIVIDUAL_PAISE,
    RATE_194O,
    RATE_PAN_PENALTY,
    THRESHOLD_MISSING_PAN_HOLD_PAISE
)

def calculate_tds(
    partner_type: str,            # 'INDIVIDUAL' or 'FIRM'
    category: str,                # 'DELIVERY' or 'SERVICE_PROFESSIONAL'
    pan_status: str,              # 'VALID', 'INVALID', 'MISSING'
    tds_base_paise: int,          # current week gross - penalties + adjustments
    fy_paid_cumulative_paise: int, # fy_paid_before + previously settled TDS bases in FY
    is_marketplace: bool,         # whether marketplace mode is active (194-O)
) -> Tuple[str, Decimal, int, bool]:
    """
    Calculate TDS section, rate, amount in paise, and missing PAN hold flag.
    Returns:
    (tds_section, tds_rate, tds_paise, is_missing_pan_hold)
    """
    if tds_base_paise <= 0:
        return "NONE", Decimal('0.0'), 0, False

    # New cumulative amount in FY including current week's base
    new_cumulative_paise = fy_paid_cumulative_paise + tds_base_paise

    # Check missing PAN hold: Missing PAN with annual cumulative payouts > Rs 50,000
    is_missing_pan_hold = (pan_status == "MISSING" and new_cumulative_paise > THRESHOLD_MISSING_PAN_HOLD_PAISE)

    tds_section = "NONE"
    rate = Decimal('0.0')

    if is_missing_pan_hold:
        # Once cumulative crosses Rs 50,000 with missing PAN, 20% applies and payout is held
        if is_marketplace:
            tds_section = "194-O"
        elif category == "SERVICE_PROFESSIONAL":
            tds_section = "194J"
        else:
            tds_section = "194C"
        rate = RATE_PAN_PENALTY

    elif is_marketplace:
        # Section 194-O applies instead of 194C and 194J
        tds_section = "194-O"
        threshold_crossed = False
        
        if partner_type == "INDIVIDUAL":
            # Annual threshold = Rs 5,00,000 for individuals only
            if new_cumulative_paise > THRESHOLD_194O_INDIVIDUAL_PAISE:
                threshold_crossed = True
        else:
            # Firm partners have no threshold under 194-O
            threshold_crossed = True

        if threshold_crossed:
            if pan_status in ("INVALID", "MISSING"):
                rate = RATE_PAN_PENALTY
            else:
                rate = RATE_194O
        else:
            rate = Decimal('0.0')

    else:
        # Standard rules: 194C for Delivery, 194J for Service Professionals
        if category == "DELIVERY":
            tds_section = "194C"
            single_exceeded = tds_base_paise > THRESHOLD_194C_SINGLE_PAISE
            annual_exceeded = new_cumulative_paise > THRESHOLD_194C_ANNUAL_PAISE

            if single_exceeded or annual_exceeded:
                if pan_status in ("INVALID", "MISSING"):
                    rate = RATE_PAN_PENALTY
                elif partner_type == "FIRM":
                    rate = RATE_194C_FIRM
                else:
                    rate = RATE_194C_INDIVIDUAL
            else:
                rate = Decimal('0.0')

        elif category == "SERVICE_PROFESSIONAL":
            tds_section = "194J"
            if new_cumulative_paise > THRESHOLD_194J_ANNUAL_PAISE:
                if pan_status in ("INVALID", "MISSING"):
                    rate = RATE_PAN_PENALTY
                else:
                    rate = RATE_194J
            else:
                rate = Decimal('0.0')

    # If rate is 0, section is NONE for reports where no tax applies,
    # or keep section name if threshold was tested.
    # Note from README: "tds_section is 194C, 194J, 194-O or NONE."
    if rate == Decimal('0.0'):
        tds_section = "NONE"
        tds_paise = 0
    else:
        # Calculate TDS on current week's base
        tds_amount_dec = (Decimal(tds_base_paise) * rate).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        tds_paise = int(tds_amount_dec)

    return tds_section, rate, tds_paise, is_missing_pan_hold
