"""Calculations module for task earnings, surge, multipliers, and date attributions."""
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from typing import Tuple

from backend.config import (
    BASE_PAY_PAISE,
    EXTRA_PER_KM_PAISE,
    BASE_DISTANCE_KM,
    CUST_CANCEL_PICKED_PAISE,
    CUST_CANCEL_UNPICKED_PAISE,
    PARTNER_CANCEL_PAISE,
    SURGE_MULTIPLIER,
    RAIN_MULTIPLIER,
    PAISE_PER_RUPEE
)

def get_week_start(event_ts_str: str) -> str:
    """
    Get the Monday (week_start) in YYYY-MM-DD for an IST event timestamp.
    Week runs Monday 00:00:00 through Sunday 23:59:59.
    """
    dt = datetime.strptime(event_ts_str.strip(), "%Y-%m-%d %H:%M:%S")
    monday = dt.date() - timedelta(days=dt.weekday())
    return monday.strftime("%Y-%m-%d")

def get_batch_date_for_week(week_start_str: str) -> str:
    """Given week_start (Monday), return settlement batch date (the following Monday)."""
    monday = datetime.strptime(week_start_str.strip(), "%Y-%m-%d").date()
    next_monday = monday + timedelta(days=7)
    return next_monday.strftime("%Y-%m-%d")

def get_week_start_for_batch(batch_date_str: str) -> str:
    """Given settlement batch date (Monday), return the previous Mon-Sun week_start (Monday)."""
    batch_monday = datetime.strptime(batch_date_str.strip(), "%Y-%m-%d").date()
    prev_monday = batch_monday - timedelta(days=7)
    return prev_monday.strftime("%Y-%m-%d")

def calculate_task_earning(
    event_type: str,
    distance_km: float | None,
    picked_up: bool | None,
    surge: bool,
    rain: bool
) -> int:
    """
    Calculate task earning in integer paise.
    Business Rules:
    - Base pay = Rs 25
    - Additional Rs 6 per km beyond 3 km
    - Surge multiplier = 1.3
    - Rain multiplier = 1.5
    - Higher multiplier applies, never stack them
    - Completed task earnings rounded half-up to nearest rupee
    - Customer cancellation after pickup = Rs 20
    - Customer cancellation before pickup = Rs 0
    - Partner cancellation = Rs 0
    """
    if event_type == "COMPLETED":
        dist = Decimal(str(distance_km)) if distance_km is not None else Decimal('0.0')
        if dist > BASE_DISTANCE_KM:
            extra_km = dist - BASE_DISTANCE_KM
            base_pay_rupees = Decimal('25') + extra_km * Decimal('6')
        else:
            base_pay_rupees = Decimal('25')

        # Multiplier determination: higher applies, never stack
        if rain:
            multiplier = RAIN_MULTIPLIER
        elif surge:
            multiplier = SURGE_MULTIPLIER
        else:
            multiplier = Decimal('1.0')

        # Round to nearest rupee half-up
        earning_rupees = (base_pay_rupees * multiplier).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        return int(earning_rupees * PAISE_PER_RUPEE)

    elif event_type == "CANCELLED_BY_CUSTOMER":
        if picked_up:
            return CUST_CANCEL_PICKED_PAISE
        return CUST_CANCEL_UNPICKED_PAISE

    elif event_type == "CANCELLED_BY_PARTNER":
        return PARTNER_CANCEL_PAISE

    return 0
