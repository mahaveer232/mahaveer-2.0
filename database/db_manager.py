"""
db_manager.py — SQLite CRUD layer for vehicles and challans tables.
"""

import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH

_CREATE_VEHICLES = """
CREATE TABLE IF NOT EXISTS vehicles (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    plate_number  TEXT    UNIQUE NOT NULL,
    owner_name    TEXT    NOT NULL,
    email         TEXT    NOT NULL,
    phone         TEXT,
    vehicle_model TEXT,
    address       TEXT
);
"""

_CREATE_CHALLANS = """
CREATE TABLE IF NOT EXISTS challans (
    id             INTEGER  PRIMARY KEY AUTOINCREMENT,
    plate_number   TEXT     NOT NULL,
    owner_name     TEXT     DEFAULT 'Unknown',
    email          TEXT     DEFAULT 'N/A',
    timestamp      DATETIME DEFAULT CURRENT_TIMESTAMP,
    violation_type TEXT     DEFAULT 'No Helmet',
    email_sent     INTEGER  DEFAULT 0
);
"""


class DatabaseManager:
    """Thread-safe SQLite database manager."""

    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self._ensure_tables()

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        """Return a new connection (check_same_thread=False for threading)."""
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tables(self):
        with self._conn() as conn:
            conn.execute(_CREATE_VEHICLES)
            conn.execute(_CREATE_CHALLANS)

    # ──────────────────────────────────────────────────────────────────────────
    # Vehicles
    # ──────────────────────────────────────────────────────────────────────────

    def get_vehicle_by_plate(self, plate: str) -> dict | None:
        """
        Look up a vehicle by plate number.
        Normalises both the query and stored values (strips spaces/dashes).
        Returns a dict or None if not found.
        """
        normalised = re.sub(r'[\s\-]', '', plate.upper()) if plate else ''
        if not normalised:
            return None

        with self._conn() as conn:
            row = conn.execute(
                """SELECT * FROM vehicles
                   WHERE UPPER(REPLACE(REPLACE(plate_number, ' ', ''), '-', ''))
                         = ?""",
                (normalised,)
            ).fetchone()

        if row:
            return dict(row)
        return None

    def get_all_vehicles(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM vehicles ORDER BY id"
            ).fetchall()
        return [dict(r) for r in rows]

    # ──────────────────────────────────────────────────────────────────────────
    # Challans
    # ──────────────────────────────────────────────────────────────────────────

    def log_challan(
        self,
        plate_number : str,
        owner_name   : str  = "Unknown",
        email        : str  = "N/A",
        email_sent   : bool = False,
    ):
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO challans
                   (plate_number, owner_name, email, email_sent)
                   VALUES (?, ?, ?, ?)""",
                (plate_number, owner_name, email, 1 if email_sent else 0)
            )

    def get_all_challans(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM challans ORDER BY timestamp DESC LIMIT 200"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_db_stats(self) -> dict:
        with self._conn() as conn:
            total_vehicles = conn.execute(
                "SELECT COUNT(*) FROM vehicles"
            ).fetchone()[0]
            total_challans = conn.execute(
                "SELECT COUNT(*) FROM challans"
            ).fetchone()[0]
            emails_sent = conn.execute(
                "SELECT COUNT(*) FROM challans WHERE email_sent = 1"
            ).fetchone()[0]
        return {
            "total_vehicles": total_vehicles,
            "total_challans": total_challans,
            "emails_sent"   : emails_sent,
        }


# ─── Late import (needed inside method) ───────────────────────────────────────
import re
