"""Partner registration, PAN validation, and CSV ingestion module."""
import csv
import io
import re
import sqlite3
from typing import Dict, Any, List, Tuple, Optional

from backend.config import rupees_to_paise

PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")

def validate_pan(pan: str) -> bool:
    """Validate Indian Permanent Account Number (PAN) format."""
    if not pan:
        return False
    return bool(PAN_REGEX.match(pan.strip().upper()))

def register_partner(
    conn: sqlite3.Connection,
    partner_id: str,
    partner_name: str,
    partner_type: str,
    category: str,
    pan_status: str,
    pan: Optional[str],
    bank_status: str,
    ifsc: str,
    city: str,
    onboarding_date: str,
    fy_paid_before: float = 0.0,
    fy_tds_before: float = 0.0,
    equipment_recovered_before: float = 0.0
) -> Dict[str, Any]:
    """Register an individual or firm partner with validation and duplicate checks."""
    partner_id = partner_id.strip()
    partner_type = partner_type.strip().upper()
    category = category.strip().upper()
    pan_status = pan_status.strip().upper()
    bank_status = bank_status.strip().upper()
    pan = pan.strip().upper() if pan else None

    # Check partner type
    if partner_type not in ("INDIVIDUAL", "FIRM"):
        raise ValueError(f"Invalid partner_type '{partner_type}'. Allowed: INDIVIDUAL, FIRM")

    # Check category
    if category not in ("DELIVERY", "SERVICE_PROFESSIONAL"):
        raise ValueError(f"Invalid category '{category}'. Allowed: DELIVERY, SERVICE_PROFESSIONAL")

    # Check PAN status and format
    if pan_status not in ("VALID", "INVALID", "MISSING"):
        raise ValueError(f"Invalid pan_status '{pan_status}'. Allowed: VALID, INVALID, MISSING")

    if pan_status == "VALID":
        if not pan or not validate_pan(pan):
            pan_status = "INVALID"
    elif pan_status == "MISSING":
        pan = None

    # Duplicate checks
    cursor = conn.cursor()
    cursor.execute("SELECT partner_id FROM partners WHERE partner_id = ?", (partner_id,))
    if cursor.fetchone():
        raise ValueError(f"Duplicate partner_id '{partner_id}' detected.")

    if pan and pan_status == "VALID":
        cursor.execute("SELECT partner_id FROM partners WHERE pan = ? AND pan_status = 'VALID'", (pan,))
        dup = cursor.fetchone()
        if dup:
            raise ValueError(f"Duplicate PAN '{pan}' already registered by partner '{dup['partner_id']}'.")

    cursor.execute("""
        INSERT INTO partners (
            partner_id, partner_name, partner_type, category, pan_status, pan,
            bank_status, ifsc, city, onboarding_date, fy_paid_before_paise,
            fy_tds_before_paise, equipment_recovered_before_paise
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        partner_id, partner_name.strip(), partner_type, category, pan_status, pan,
        bank_status, ifsc.strip(), city.strip(), onboarding_date.strip(),
        rupees_to_paise(fy_paid_before), rupees_to_paise(fy_tds_before),
        rupees_to_paise(equipment_recovered_before)
    ))

    return {
        "partner_id": partner_id,
        "partner_name": partner_name,
        "partner_type": partner_type,
        "category": category,
        "pan_status": pan_status,
        "pan": pan,
        "bank_status": bank_status
    }

def ingest_partners_csv(conn: sqlite3.Connection, csv_content: str) -> Dict[str, Any]:
    """Ingest partners from CSV content string with schema validation and error reporting."""
    reader = csv.DictReader(io.StringIO(csv_content))
    required_fields = {
        "partner_id", "partner_name", "partner_type", "category",
        "pan_status", "pan", "bank_status", "ifsc", "city",
        "onboarding_date", "fy_paid_before", "fy_tds_before",
        "equipment_recovered_before"
    }

    if not reader.fieldnames or not required_fields.issubset(set(reader.fieldnames)):
        missing = required_fields - set(reader.fieldnames or [])
        raise ValueError(f"partners.csv missing required headers: {missing}")

    successful = 0
    errors: List[Dict[str, Any]] = []

    for row_num, row in enumerate(reader, start=1):
        try:
            register_partner(
                conn=conn,
                partner_id=row["partner_id"],
                partner_name=row["partner_name"],
                partner_type=row["partner_type"],
                category=row["category"],
                pan_status=row["pan_status"],
                pan=row.get("pan"),
                bank_status=row["bank_status"],
                ifsc=row["ifsc"],
                city=row["city"],
                onboarding_date=row["onboarding_date"],
                fy_paid_before=float(row.get("fy_paid_before") or 0.0),
                fy_tds_before=float(row.get("fy_tds_before") or 0.0),
                equipment_recovered_before=float(row.get("equipment_recovered_before") or 0.0)
            )
            successful += 1
        except Exception as e:
            errors.append({"row": row_num, "partner_id": row.get("partner_id"), "error": str(e)})

    return {"successful": successful, "errors": errors, "total_rows": row_num if 'row_num' in locals() else 0}
