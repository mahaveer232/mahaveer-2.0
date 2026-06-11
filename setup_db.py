"""
setup_db.py -- Run once to initialize the SQLite database and seed 20 demo vehicle records.
Usage: python setup_db.py
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DB_PATH

# ─── 20 Demo Indian Vehicle Records ───────────────────────────────────────────
# Format: (plate_number, owner_name, email, phone, vehicle_model, address)
DEMO_VEHICLES = [
    ("MH12AB1234", "Rajesh Kumar",     "rtoheadquarters@gmail.com",     "9876543210", "Honda Activa 6G",         "123, MG Road, Pune, Maharashtra 411001"),
    ("DL5SAF1235", "Priya Sharma",     "priya.sharma.test@gmail.com",   "9765432109", "TVS Jupiter Classic",     "45, Lajpat Nagar-II, New Delhi 110024"),
    ("KA03MJ7654", "Amit Patel",       "amit.patel.test@gmail.com",     "9654321098", "Bajaj Pulsar 150",        "78, Brigade Road, Bengaluru, Karnataka 560001"),
    ("UP14CR4321", "Sunita Devi",      "sunita.devi.test@gmail.com",    "9543210987", "Hero Splendor Plus",      "12, Civil Lines, Lucknow, UP 226001"),
    ("GJ01AA9999", "Vikram Singh",     "vikram.singh.test@gmail.com",   "9432109876", "Honda Shine 125",         "55, SG Highway, Ahmedabad, Gujarat 380015"),
    ("RJ14BT5678", "Meena Kumari",     "meena.kumari.test@gmail.com",   "9321098765", "TVS Apache RTR 160",      "33, MI Road, Jaipur, Rajasthan 302001"),
    ("TN09CC3456", "Karthik Rajan",    "karthik.rajan.test@gmail.com",  "9210987654", "Royal Enfield Classic 350","88, Anna Salai, Chennai, Tamil Nadu 600002"),
    ("MH04DE2345", "Pooja Nair",       "pooja.nair.test@gmail.com",     "9109876543", "Suzuki Access 125",       "21, Bandra West, Mumbai, Maharashtra 400050"),
    ("PB07FF6543", "Gurpreet Singh",   "gurpreet.s.test@gmail.com",     "9098765432", "Hero HF Deluxe",          "66, GT Road, Ludhiana, Punjab 141001"),
    ("TS28GH7890", "Lakshmi Reddy",    "lakshmi.reddy.test@gmail.com",  "8987654321", "Honda CB Unicorn 160",    "44, Banjara Hills, Hyderabad, Telangana 500034"),
    ("MH14IJ1122", "Suresh Patil",     "suresh.patil.test@gmail.com",   "8876543210", "Yamaha FZ-S V3",          "99, FC Road, Pune, Maharashtra 411004"),
    ("DL8CAF3344", "Anita Gupta",      "anita.gupta.test@gmail.com",    "8765432109", "Honda Dio 110",           "77, Rohini Sector 3, New Delhi 110085"),
    ("WB06KL5566", "Dipankar Das",     "dipankar.das.test@gmail.com",   "8654321098", "Bajaj Avenger 220",       "11, Park Street, Kolkata, West Bengal 700016"),
    ("HR26MN7788", "Rahul Yadav",      "rahul.yadav.test@gmail.com",    "8543210987", "TVS Victor Premium",      "22, Sohna Road, Gurgaon, Haryana 122001"),
    ("MP09OP9900", "Kavita Verma",     "kavita.verma.test@gmail.com",   "8432109876", "Hero Passion Pro",        "44, Arera Colony, Bhopal, MP 462016"),
    ("OR02QR1234", "Subhash Mohanta",  "subhash.m.test@gmail.com",      "8321098765", "Honda Livo 110",          "55, Station Square, Bhubaneswar, Odisha 751006"),
    ("JH10ST5678", "Ravi Tiwari",      "ravi.tiwari.test@gmail.com",    "8210987654", "Bajaj CT100 B",           "66, Main Road, Ranchi, Jharkhand 834001"),
    ("CH01UV9012", "Neha Malhotra",    "neha.malhotra.test@gmail.com",  "8109876543", "Yamaha Ray-ZR 125",       "33, Sector 17, Chandigarh 160017"),
    ("GJ05WX3456", "Harish Chauhan",   "harish.c.test@gmail.com",       "8098765432", "Honda CD 110 Dream",      "77, Ring Road, Surat, Gujarat 395002"),
    ("MH20YZ7890", "Deepak Sharma",    "deepak.sharma.test@gmail.com",  "7987654321", "KTM Duke 200",            "88, Viman Nagar, Pune, Maharashtra 411014"),
]

CREATE_VEHICLES_SQL = """
CREATE TABLE IF NOT EXISTS vehicles (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    plate_number TEXT    UNIQUE NOT NULL,
    owner_name   TEXT    NOT NULL,
    email        TEXT    NOT NULL,
    phone        TEXT,
    vehicle_model TEXT,
    address      TEXT
);
"""

CREATE_CHALLANS_SQL = """
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


def setup_database():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    print(f"[DB] Initializing database at: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(CREATE_VEHICLES_SQL)
        conn.execute(CREATE_CHALLANS_SQL)
        conn.commit()
        print("[DB] Tables created (or already exist).")

        inserted = 0
        skipped  = 0
        for vehicle in DEMO_VEHICLES:
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO vehicles
                       (plate_number, owner_name, email, phone, vehicle_model, address)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    vehicle
                )
                if conn.execute("SELECT changes()").fetchone()[0]:
                    inserted += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"  [WARN] Could not insert {vehicle[0]}: {e}")
        conn.commit()

        total = conn.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0]
        print(f"[DB] Inserted: {inserted}  |  Already existed: {skipped}")
        print(f"[DB] Total vehicle records: {total}")
        print("\n[DB] >> Database setup complete!")
        print("[DB]    Run 'python app.py' to start the server.\n")
    finally:
        conn.close()


if __name__ == "__main__":
    setup_database()
