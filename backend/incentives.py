"""Weekly incentives module."""
from decimal import Decimal, ROUND_HALF_UP
from typing import Tuple

from backend.config import (
    INCENTIVE_TIERS,
    MAX_CANCELLATION_RATE_PCT,
    MIN_AVG_RATING
)

def calculate_weekly_incentive(
    completed_count: int,
    cancellation_rate_pct: Decimal,
    avg_rating: Decimal | None
) -> Tuple[int, str]:
    """
    Calculate eligible weekly incentive in paise and return reason if forfeited.
    Tiers:
    - >= 120 tasks: Rs 2000
    - >= 90 tasks:  Rs 1200
    - >= 60 tasks:  Rs 600
    
    Forfeits if:
    - cancellation_rate_pct > 8.00% (strictly greater than 8.00%)
    - avg_rating is not None and avg_rating < 4.20
    """
    eligible_paise = 0
    for min_tasks, incentive_paise in INCENTIVE_TIERS:
        if completed_count >= min_tasks:
            eligible_paise = incentive_paise
            break

    if eligible_paise == 0:
        return 0, "No tier threshold reached"

    # Forfeit check: cancellation rate exceeds 8%
    if cancellation_rate_pct > MAX_CANCELLATION_RATE_PCT:
        return 0, f"Forfeited: cancellation rate {cancellation_rate_pct:.2f}% exceeds {MAX_CANCELLATION_RATE_PCT}%"

    # Forfeit check: average rating below 4.2
    if avg_rating is not None and avg_rating < MIN_AVG_RATING:
        return 0, f"Forfeited: average rating {avg_rating:.2f} is below {MIN_AVG_RATING}"

    return eligible_paise, "Eligible"
