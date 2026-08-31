"""
Extract median annual pay by local authority from ASHE Table 8.7a
(Annual pay - Gross, "All" employee jobs sheet) across multiple years,
and combine into one long-format CSV: year, la_code, la_name, median_pay,
mean_pay, number_of_jobs_thousands.

Only rows with a genuine local authority ONS code are kept (English
unitary/district/metropolitan/London borough/county codes E06/E07/E08/
E09/E10, and Welsh unitary codes W06). National and regional aggregate
rows (UK, Great Britain, England, North East, etc.) are dropped, since
they'd otherwise sit in the same column and get mistaken for LA-level
data.

Rows where ONS suppressed the median (sample too small, shown as blank
or 'x' in the source) are kept with median_pay = NULL, not dropped and
not estimated, that's the honest way to represent it.
"""
import glob
import os
import re
import sys

import pandas as pd

RAW_DIR = "data/raw/ashe_table8"
OUT_PATH = "data/processed/ashe_median_pay_by_la_year.csv"

LA_CODE_PATTERN = re.compile(r"^(E0[6-9]|E10|W06)\d{6}$")


def find_year_file(year_dir):
    matches = glob.glob(os.path.join(year_dir, "*8.7a*"))
    if not matches:
        return None
    return matches[0]


def extract_year(path, year):
    df = pd.read_excel(path, sheet_name="All", header=None)

    header_row = None
    for i in range(min(10, len(df))):
        row_vals = df.iloc[i].astype(str).tolist()
        if "Description" in row_vals and "Code" in row_vals:
            header_row = i
            break
    if header_row is None:
        raise ValueError(f"Could not find header row in {path}")

    header = df.iloc[header_row].tolist()
    data = df.iloc[header_row + 1:].copy()
    data.columns = header
    data = data.reset_index(drop=True)

    data = data.rename(columns={
        "Description": "la_name",
        "Code": "la_code",
        "Median": "median_pay",
        "Mean": "mean_pay",
    })

    # ONS splits the "Number of jobs (thousand)" header across three merged
    # rows above the single row we used to locate columns by text, so the
    # text in our header row for this column is just a fragment (e.g.
    # "(thousand)"). It is always the 3rd column (index 2) in this table's
    # fixed layout, so grab it positionally instead of by text match.
    jobs_col_index = 2
    data = data.rename(columns={data.columns[jobs_col_index]: "number_of_jobs_thousands"})

    data["la_code"] = data["la_code"].astype(str).str.strip()
    data = data[data["la_code"].apply(lambda c: bool(LA_CODE_PATTERN.match(c)))]

    for col in ["median_pay", "mean_pay", "number_of_jobs_thousands"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data["la_name"] = data["la_name"].astype(str).str.strip()
    data["year"] = year

    return data[["year", "la_code", "la_name", "median_pay", "mean_pay", "number_of_jobs_thousands"]]


def main():
    year_dirs = sorted(
        d for d in glob.glob(os.path.join(RAW_DIR, "*"))
        if os.path.isdir(d) and os.path.basename(d).isdigit()
    )
    if not year_dirs:
        print(f"No year folders found under {RAW_DIR}", file=sys.stderr)
        sys.exit(1)

    frames = []
    for year_dir in year_dirs:
        year = int(os.path.basename(year_dir))
        path = find_year_file(year_dir)
        if not path:
            print(f"WARNING: no Table 8.7a file found for {year}, skipping", file=sys.stderr)
            continue
        print(f"extracting {year} from {path}")
        frames.append(extract_year(path, year))

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(["la_name", "year"])
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    combined.to_csv(OUT_PATH, index=False)

    total = len(combined)
    missing = combined["median_pay"].isna().sum()
    print(f"wrote {OUT_PATH}: {total} rows across {combined['year'].nunique()} years, "
          f"{combined['la_code'].nunique()} local authorities, "
          f"{missing} rows with suppressed/missing median ({missing/total:.1%})")


if __name__ == "__main__":
    main()
