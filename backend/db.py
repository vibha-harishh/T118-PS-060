"""Database initialization and connection management using SQLite."""
import sqlite3
import os
from typing import Generator
from contextlib import contextmanager

def get_db_path() -> str:
    return os.environ.get("SQLITE_DB_PATH", "/app/applet/payout_engine.db")

def get_db_connection() -> sqlite3.Connection:
    """Create a SQLite connection with foreign keys and row factory."""
    conn = sqlite3.connect(get_db_path())
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def transaction() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for atomic database transactions."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db(drop_all: bool = False) -> None:
    """Initialize SQLite database tables, indexes, and constraints."""
    with transaction() as conn:
        cursor = conn.cursor()
        
        if drop_all:
            cursor.executescript("""
                DROP TABLE IF EXISTS bank_returns;
                DROP TABLE IF EXISTS ledger_entries;
                DROP TABLE IF EXISTS weekly_statements;
                DROP TABLE IF EXISTS settlement_batches;
                DROP TABLE IF EXISTS adjustments;
                DROP TABLE IF EXISTS complaints;
                DROP TABLE IF EXISTS task_events;
                DROP TABLE IF EXISTS slots;
                DROP TABLE IF EXISTS partners;
                DROP TABLE IF EXISTS marketplace_periods;
                DROP TABLE IF EXISTS platform_settings;
            """)
        
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS partners (
                partner_id TEXT PRIMARY KEY,
                partner_name TEXT NOT NULL,
                partner_type TEXT NOT NULL CHECK(partner_type IN ('INDIVIDUAL', 'FIRM')),
                category TEXT NOT NULL CHECK(category IN ('DELIVERY', 'SERVICE_PROFESSIONAL')),
                pan_status TEXT NOT NULL CHECK(pan_status IN ('VALID', 'INVALID', 'MISSING')),
                pan TEXT,
                bank_status TEXT NOT NULL CHECK(bank_status IN ('VERIFIED', 'UNVERIFIED')),
                ifsc TEXT NOT NULL,
                city TEXT NOT NULL,
                onboarding_date TEXT NOT NULL,
                fy_paid_before_paise INTEGER NOT NULL DEFAULT 0,
                fy_tds_before_paise INTEGER NOT NULL DEFAULT 0,
                equipment_recovered_before_paise INTEGER NOT NULL DEFAULT 0,
                is_held_manual INTEGER NOT NULL DEFAULT 0,
                manual_hold_reason TEXT,
                bank_retry_count INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS slots (
                slot_id TEXT PRIMARY KEY,
                city TEXT NOT NULL,
                slot_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                surge INTEGER NOT NULL DEFAULT 0,
                rain INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS task_events (
                event_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                partner_id TEXT NOT NULL REFERENCES partners(partner_id),
                event_type TEXT NOT NULL CHECK(event_type IN ('COMPLETED', 'CANCELLED_BY_CUSTOMER', 'CANCELLED_BY_PARTNER')),
                event_ts TEXT NOT NULL,
                slot_id TEXT REFERENCES slots(slot_id),
                distance_km REAL,
                picked_up INTEGER,
                rating INTEGER,
                week_start TEXT NOT NULL,
                task_earnings_paise INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                partner_id TEXT NOT NULL REFERENCES partners(partner_id),
                task_id TEXT NOT NULL,
                complaint_ts TEXT NOT NULL,
                reason TEXT,
                week_start TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS adjustments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                partner_id TEXT NOT NULL REFERENCES partners(partner_id),
                week_start TEXT NOT NULL,
                amount_paise INTEGER NOT NULL,
                reference TEXT NOT NULL,
                adjustment_ts TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('ACCEPTED', 'REJECTED')),
                rejection_reason TEXT
            );

            CREATE TABLE IF NOT EXISTS marketplace_periods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                effective_date TEXT NOT NULL UNIQUE,
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS settlement_batches (
                batch_date TEXT PRIMARY KEY,
                processed_ts TEXT NOT NULL,
                partners_paid INTEGER NOT NULL DEFAULT 0,
                amount_paid_paise INTEGER NOT NULL DEFAULT 0,
                partners_held INTEGER NOT NULL DEFAULT 0,
                amount_held_paise INTEGER NOT NULL DEFAULT 0,
                carried_forward_paise INTEGER NOT NULL DEFAULT 0,
                retries INTEGER NOT NULL DEFAULT 0,
                tds_total_paise INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS weekly_statements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                partner_id TEXT NOT NULL REFERENCES partners(partner_id),
                week_start TEXT NOT NULL,
                batch_date TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                cancelled_by_partner INTEGER NOT NULL DEFAULT 0,
                cancelled_by_customer INTEGER NOT NULL DEFAULT 0,
                cancellation_rate_pct REAL NOT NULL DEFAULT 0.0,
                avg_rating REAL NOT NULL DEFAULT 0.0,
                task_earnings_paise INTEGER NOT NULL DEFAULT 0,
                incentive_paise INTEGER NOT NULL DEFAULT 0,
                gross_paise INTEGER NOT NULL DEFAULT 0,
                penalties_paise INTEGER NOT NULL DEFAULT 0,
                penalty_cap_paise INTEGER NOT NULL DEFAULT 0,
                adjustments_paise INTEGER NOT NULL DEFAULT 0,
                tds_base_paise INTEGER NOT NULL DEFAULT 0,
                tds_section TEXT NOT NULL DEFAULT 'NONE',
                tds_rate_pct REAL NOT NULL DEFAULT 0.0,
                tds_paise INTEGER NOT NULL DEFAULT 0,
                equipment_deduction_paise INTEGER NOT NULL DEFAULT 0,
                carry_in_paise INTEGER NOT NULL DEFAULT 0,
                net_payable_paise INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                UNIQUE(partner_id, week_start)
            );

            CREATE TABLE IF NOT EXISTS ledger_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                partner_id TEXT NOT NULL REFERENCES partners(partner_id),
                entry_ts TEXT NOT NULL,
                entry_type TEXT NOT NULL,
                week_start TEXT,
                amount_paise INTEGER NOT NULL,
                earned_to_date_paise INTEGER NOT NULL DEFAULT 0,
                withheld_to_date_paise INTEGER NOT NULL DEFAULT 0,
                paid_to_date_paise INTEGER NOT NULL DEFAULT 0,
                recovered_to_date_paise INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS bank_returns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                partner_id TEXT NOT NULL REFERENCES partners(partner_id),
                batch_date TEXT NOT NULL,
                return_ts TEXT NOT NULL,
                reason TEXT NOT NULL,
                retry_number INTEGER NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_tasks_week ON task_events(week_start, partner_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_partner ON task_events(partner_id);
            CREATE INDEX IF NOT EXISTS idx_statements_week ON weekly_statements(week_start);
            CREATE INDEX IF NOT EXISTS idx_statements_partner ON weekly_statements(partner_id);
            CREATE INDEX IF NOT EXISTS idx_ledger_partner ON ledger_entries(partner_id, entry_ts);
        """)
