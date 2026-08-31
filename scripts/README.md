# Price Paid Data load

`load_price_paid.py` streams HM Land Registry's `pp-complete.csv` (1995-present,
no header row) into a SQLite database, keeping only:

- Category A transactions (standard residential sales; excludes repossessions,
  buy-to-let portfolio deals and other non-market-value "additional" entries)
- Transactions with year 2015 through 2026 inclusive

Usage (resumable, run repeatedly until it prints `done=True`):

    python3 load_price_paid.py <csv_path> <db_path> A <state_json_path> <seconds_per_chunk>

State (byte offset + running counts) is saved to the state JSON file so the
load can be safely interrupted and resumed without double-counting rows
(inserts use INSERT OR IGNORE keyed on the transaction's unique GUID).

Result: `db/price_paid.sqlite`, table `price_paid`, 9,760,341 rows
(2015-2026, category A), indexed on (district, year).

Source file: `data/pp-complete.csv`, downloaded manually from
https://www.gov.uk/government/statistical-data-sets/price-paid-data-single-file
(complete file, 5.51GB, includes 1995-2026; this script filters it down).

Caveat: 2026 figures are undercounted due to HM Land Registry's registration
lag (sales take weeks to months to appear in the bulk file after completion).
