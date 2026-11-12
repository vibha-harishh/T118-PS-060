"""Slot and Task event ingestion module."""
import csv
import io
import sqlite3
from typing import Dict, Any, List, Optional

from backend.calculations import calculate_task_earning, get_week_start

def ingest_slots_csv(conn: sqlite3.Connection, csv_content: str) -> Dict[str, Any]:
    """Ingest slots from CSV content with surge and rain boolean flags."""
    reader = csv.DictReader(io.StringIO(csv_content))
    required_fields = {"slot_id", "city", "slot_date", "start_time", "end_time", "surge", "rain"}

    if not reader.fieldnames or not required_fields.issubset(set(reader.fieldnames)):
        missing = required_fields - set(reader.fieldnames or [])
        raise ValueError(f"slots.csv missing required headers: {missing}")

    cursor = conn.cursor()
    successful = 0
    errors: List[Dict[str, Any]] = []

    for row_num, row in enumerate(reader, start=1):
        try:
            slot_id = row["slot_id"].strip()
            city = row["city"].strip()
            slot_date = row["slot_date"].strip()
            start_time = row["start_time"].strip()
            end_time = row["end_time"].strip()
            surge = 1 if row["surge"].strip().lower() in ("true", "1") else 0
            rain = 1 if row["rain"].strip().lower() in ("true", "1") else 0

            cursor.execute("""
                INSERT INTO slots (slot_id, city, slot_date, start_time, end_time, surge, rain)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(slot_id) DO UPDATE SET
                    city = excluded.city,
                    slot_date = excluded.slot_date,
                    start_time = excluded.start_time,
                    end_time = excluded.end_time,
                    surge = excluded.surge,
                    rain = excluded.rain
            """, (slot_id, city, slot_date, start_time, end_time, surge, rain))
            successful += 1
        except Exception as e:
            errors.append({"row": row_num, "slot_id": row.get("slot_id"), "error": str(e)})

    return {"successful": successful, "errors": errors, "total_rows": row_num if 'row_num' in locals() else 0}

def ingest_task_events_csv(conn: sqlite3.Connection, csv_content: str) -> Dict[str, Any]:
    """
    Ingest task events from CSV content.
    Deduplicates identical events (e.g. EV-00905), computes earnings, and attributes week.
    """
    reader = csv.DictReader(io.StringIO(csv_content))
    required_fields = {
        "event_id", "task_id", "partner_id", "event_type",
        "event_ts", "slot_id", "distance_km", "picked_up", "rating"
    }

    if not reader.fieldnames or not required_fields.issubset(set(reader.fieldnames)):
        missing = required_fields - set(reader.fieldnames or [])
        raise ValueError(f"task_events.csv missing required headers: {missing}")

    cursor = conn.cursor()
    successful = 0
    duplicates_skipped = 0
    errors: List[Dict[str, Any]] = []

    # Cache slots for speed
    cursor.execute("SELECT slot_id, surge, rain FROM slots")
    slot_cache = {row["slot_id"]: (bool(row["surge"]), bool(row["rain"])) for row in cursor.fetchall()}

    for row_num, row in enumerate(reader, start=1):
        try:
            event_id = row["event_id"].strip()

            # Duplicate check
            cursor.execute("SELECT event_id FROM task_events WHERE event_id = ?", (event_id,))
            if cursor.fetchone():
                duplicates_skipped += 1
                continue

            task_id = row["task_id"].strip()
            partner_id = row["partner_id"].strip()
            event_type = row["event_type"].strip().upper()
            event_ts = row["event_ts"].strip()
            slot_id = row["slot_id"].strip() if row.get("slot_id") else None

            distance_km = float(row["distance_km"]) if row.get("distance_km") else None
            picked_up = row.get("picked_up", "").strip().lower() in ("true", "1") if row.get("picked_up") else None
            rating = int(row["rating"]) if row.get("rating") and row["rating"].strip() else None

            # Get surge / rain for slot
            surge, rain = slot_cache.get(slot_id, (False, False)) if slot_id else (False, False)

            # Compute task earnings in paise
            task_earning_paise = calculate_task_earning(
                event_type=event_type,
                distance_km=distance_km,
                picked_up=picked_up,
                surge=surge,
                rain=rain
            )

            # Week start (Monday of the event's week)
            week_start = get_week_start(event_ts)

            cursor.execute("""
                INSERT INTO task_events (
                    event_id, task_id, partner_id, event_type, event_ts,
                    slot_id, distance_km, picked_up, rating, week_start,
                    task_earnings_paise
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id, task_id, partner_id, event_type, event_ts,
                slot_id, distance_km, 1 if picked_up else 0 if picked_up is not None else None,
                rating, week_start, task_earning_paise
            ))
            successful += 1
        except Exception as e:
            errors.append({"row": row_num, "event_id": row.get("event_id"), "error": str(e)})

    return {
        "successful": successful,
        "duplicates_skipped": duplicates_skipped,
        "errors": errors,
        "total_rows": row_num if 'row_num' in locals() else 0
    }
