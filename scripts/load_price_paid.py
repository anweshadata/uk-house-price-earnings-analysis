import csv
import io
import json
import os
import sqlite3
import sys
import time

CSV_PATH = sys.argv[1]
DB_PATH = sys.argv[2]
CATEGORY_FILTER = sys.argv[3] if len(sys.argv) > 3 else "A"
STATE_PATH = sys.argv[4]
TIME_BUDGET = float(sys.argv[5]) if len(sys.argv) > 5 else 120.0

MIN_YEAR = 2015
MAX_YEAR = 2026
allowed_categories = set(CATEGORY_FILTER)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("PRAGMA journal_mode = WAL;")
cur.execute("PRAGMA synchronous = OFF;")
cur.execute("""
CREATE TABLE IF NOT EXISTS price_paid (
    transaction_id   TEXT PRIMARY KEY,
    price             INTEGER,
    date_of_transfer  TEXT,
    year              INTEGER,
    postcode          TEXT,
    property_type     TEXT,
    old_new           TEXT,
    duration          TEXT,
    paon              TEXT,
    saon              TEXT,
    street            TEXT,
    locality          TEXT,
    town_city         TEXT,
    district          TEXT,
    county             TEXT,
    ppd_category_type TEXT,
    record_status     TEXT
);
""")
conn.commit()

if os.path.exists(STATE_PATH):
    with open(STATE_PATH) as sf:
        state = json.load(sf)
    start_offset = state.get("offset", 0)
    total_read = state.get("total_read", 0)
    total_kept = state.get("total_kept", 0)
else:
    start_offset = 0
    total_read = 0
    total_kept = 0

insert_sql = """
INSERT OR IGNORE INTO price_paid
(transaction_id, price, date_of_transfer, year, postcode, property_type, old_new,
 duration, paon, saon, street, locality, town_city, district, county,
 ppd_category_type, record_status)
VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
"""

start_time = time.time()
batch = []
BATCH_SIZE = 20000
done = False

with open(CSV_PATH, newline='', encoding='utf-8', errors='replace') as f:
    f.seek(start_offset)
    while True:
        pos_before = f.tell()
        line = f.readline()
        if not line:
            done = True
            break
        total_read += 1

        row = next(csv.reader(io.StringIO(line)), None)
        if row and len(row) == 16:
            (txn_id, price, date_str, postcode, prop_type, old_new, duration,
             paon, saon, street, locality, town_city, district, county,
             ppd_cat, record_status) = row

            if ppd_cat in allowed_categories:
                try:
                    year = int(date_str[:4])
                except (ValueError, IndexError):
                    year = None
                if year is not None and MIN_YEAR <= year <= MAX_YEAR:
                    try:
                        price_int = int(price)
                        batch.append((txn_id, price_int, date_str, year, postcode, prop_type,
                                      old_new, duration, paon, saon, street, locality, town_city,
                                      district, county, ppd_cat, record_status))
                        total_kept += 1
                    except ValueError:
                        pass

        if len(batch) >= BATCH_SIZE:
            cur.executemany(insert_sql, batch)
            conn.commit()
            batch.clear()

        if total_read % 100000 == 0:
            if time.time() - start_time > TIME_BUDGET:
                current_offset = f.tell()
                break
    else:
        current_offset = f.tell()

    if not done:
        current_offset = f.tell()
    else:
        current_offset = f.tell()

if batch:
    cur.executemany(insert_sql, batch)
    conn.commit()
    batch.clear()

conn.close()

with open(STATE_PATH, "w") as sf:
    json.dump({"offset": current_offset, "total_read": total_read, "total_kept": total_kept, "done": done}, sf)

elapsed = time.time() - start_time
print(f"chunk_done done={done} read={total_read:,} kept={total_kept:,} offset={current_offset:,} elapsed={elapsed:.0f}s", flush=True)
