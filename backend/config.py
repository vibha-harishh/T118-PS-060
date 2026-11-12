"""Configuration constants and monetary helpers for Gig-Worker Payout Engine."""
from decimal import Decimal, ROUND_HALF_UP

PAISE_PER_RUPEE = Decimal('100')

def rupees_to_paise(rupees: Decimal | float | int | str) -> int:
    """Convert Rupee amount to integer paise with half-up rounding."""
    if rupees is None or rupees == '':
        return 0
    d = Decimal(str(rupees))
    return int((d * PAISE_PER_RUPEE).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

def paise_to_rupees(paise: int | None) -> Decimal:
    """Convert integer paise to Decimal Rupees with 2 decimal places."""
    if paise is None:
        return Decimal('0.00')
    return (Decimal(paise) / PAISE_PER_RUPEE).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def format_rupees(paise: int | None) -> str:
    """Format integer paise to standard 2-decimal rupee string."""
    return f"{paise_to_rupees(paise):.2f}"

# Business Rule Constants
BASE_PAY_PAISE = 2500                     # Rs 25
EXTRA_PER_KM_PAISE = 600                  # Rs 6
BASE_DISTANCE_KM = Decimal('3.0')
CUST_CANCEL_PICKED_PAISE = 2000           # Rs 20
CUST_CANCEL_UNPICKED_PAISE = 0
PARTNER_CANCEL_PAISE = 0

SURGE_MULTIPLIER = Decimal('1.3')
RAIN_MULTIPLIER = Decimal('1.5')

INCENTIVE_TIERS = [
    (120, 200000),  # 120 tasks -> Rs 2000 (in paise)
    (90, 120000),   # 90 tasks -> Rs 1200
    (60, 60000),    # 60 tasks -> Rs 600
]

MAX_CANCELLATION_RATE_PCT = Decimal('8.00')  # > 8.00% forfeits
MIN_AVG_RATING = Decimal('4.20')              # < 4.20 forfeits

FREE_PARTNER_CANCELLATIONS = 3
PENALTY_PER_EXTRA_CANCEL_PAISE = 5000       # Rs 50
COMPLAINT_PENALTY_PAISE = 20000             # Rs 200
PENALTY_CAP_RATIO = Decimal('0.20')         # 20% of gross earnings

EQUIPMENT_WEEKLY_DEDUCTION_PAISE = 15000    # Rs 150
EQUIPMENT_MAX_RECOVERY_PAISE = 180000       # Rs 1800
EQUIPMENT_PAUSE_THRESHOLD_PAISE = 100000    # Pause if net before TDS < Rs 1000

MAX_ADJUSTMENT_PAISE = 200000               # Rs 2000 max signed adjustment
MIN_PAYOUT_THRESHOLD_PAISE = 20000          # Rs 200 minimum payout threshold

# TDS Thresholds & Rates
THRESHOLD_194C_SINGLE_PAISE = 3000000       # > Rs 30,000 single payment
THRESHOLD_194C_ANNUAL_PAISE = 10000000      # > Rs 1,00,000 annual cumulative
RATE_194C_INDIVIDUAL = Decimal('0.01')
RATE_194C_FIRM = Decimal('0.02')

THRESHOLD_194J_ANNUAL_PAISE = 3000000       # > Rs 30,000 annual cumulative
RATE_194J = Decimal('0.10')

THRESHOLD_194O_INDIVIDUAL_PAISE = 50000000  # > Rs 5,00,000 annual for individuals only
RATE_194O = Decimal('0.01')

RATE_PAN_PENALTY = Decimal('0.20')          # 20% for INVALID or MISSING PAN
THRESHOLD_MISSING_PAN_HOLD_PAISE = 5000000  # Cumulative > Rs 50,000 holds payout until PAN supplied

BANK_RETRY_CHARGE_PAISE = 1000              # Rs 10 bank retry charge
MAX_BANK_RETRIES = 2
