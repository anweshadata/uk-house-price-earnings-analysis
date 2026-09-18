# UK House Price vs. Earnings Analysis

A data pipeline and Power BI dashboard comparing median house prices to median local earnings across every local authority in England and Wales, 2015-2025, to look at how housing affordability (price-to-earnings ratio) has moved over time.

## Data sources

- House prices: [HM Land Registry Price Paid Data](https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads) (`pp-complete.csv`), filtered to standard residential sales (PPD Category Type A) for 2015-2026.
- Earnings: [ONS Annual Survey of Hours and Earnings (ASHE), Table 8.7a](https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/earningsandworkinghours), "Annual pay - Gross", all employee jobs, place of residence basis, 2015-2025.

Both are official UK government statistics, publicly available for reuse.

## Pipeline

```
scripts/load_price_paid.py       -> price_paid.sqlite      (raw price paid data, filtered & indexed)
sql/median_price_by_la_year.sql  -> data/processed/median_price_by_la_year.csv
scripts/extract_ashe_table8.py   -> data/processed/ashe_median_pay_by_la_year.csv
scripts/build_la_lookup.py       -> data/processed/la_lookup.csv (+ la_lookup_unmatched_price_paid.csv)
scripts/build_joined_table.py    -> data/processed/price_vs_earnings_by_la_year.csv   (final output)
```

Run in that order. Each script/query only needs the outputs of the ones before it, so the pipeline is fully reproducible from the two raw source files.

## Reproducing this from scratch

1. Download `pp-complete.csv` from the Land Registry link above, and the Table 8.7a workbook for each year (2015-2025) from the ONS link above into `data/raw/ashe_table8/<year>/`.
2. `python scripts/load_price_paid.py` to build the SQLite database.
3. Run `sql/median_price_by_la_year.sql` against it (e.g. in DB Browser for SQLite, or via the `sqlite3` Python module) and save the result as `data/processed/median_price_by_la_year.csv`.
4. `python scripts/extract_ashe_table8.py`
5. `python scripts/build_la_lookup.py`
6. `python scripts/build_joined_table.py`

`pp-complete.csv` and the generated `.sqlite` database are not included in this repository (multi-gigabyte files, regenerable from the steps above) - see `.gitignore`.

## Requirements

See `requirements.txt`. Only `extract_ashe_table8.py` needs third-party packages (pandas, to read the ASHE Excel workbooks); the rest of the pipeline uses only the Python standard library (`sqlite3`, `csv`, `re`).

## Key methodology notes

- Median (not mean) is used for both price and pay, since both are right-skewed distributions.
- House prices and earnings are joined on ONS `la_code` (a stable geography code), not on local authority name, because names change across years due to local government reorganisation.
- Matching between Land Registry's plain-text `district` field and ASHE's `la_code` is done per year, not globally, so that a name pointing to different local authorities in different years is resolved correctly rather than flagged as ambiguous.
- Blaenau Gwent's English and Welsh names are officially identical (per Welsh Government terminology), unlike other bilingual local authority names (e.g. Merthyr Tydfil/Merthyr Tudful). The joined dataset originally rendered this as "Blaenau Gwent / Blaenau Gwent"; the dashboard displays it as "Blaenau Gwent" (display-layer fix only, source data unchanged).

Full details, including every local government reorganisation case identified and how it was handled, are in `docs/data_limitations.md` - read this before drawing conclusions from the output, especially for districts that were affected by local government reorganisation (e.g. Buckinghamshire, Dorset, Somerset, North Yorkshire, Cumbria).

## Project structure

```
data/
  raw/ashe_table8/<year>/   ASHE Table 8.7a source workbooks (2015-2025)
  processed/                 all generated CSV outputs
docs/
  data_limitations.md        data quality caveats and methodology decisions
  power_bi_setup.md          column type corrections and null-handling approach
scripts/                     the pipeline scripts described above
sql/                         the SQL query used to compute median prices
dashboard/                   dashboard screenshots (see below)
```

## Dashboard

Built in Power BI on `price_vs_earnings_by_la_year.csv`. Shared here as static screenshots rather than the `.pbix` file itself (too large to distribute); the `.pbix` is built locally by importing the CSV per `docs/power_bi_setup.md`.

Four pages, plus one hidden methodology page (also included as a screenshot below). Colour convention used throughout: **green = more affordable, red = less affordable**, based on the price-to-earnings ratio.

1. **Overview** - national KPI cards, an 11-year affordability ratio trend line, and a year selector.
2. **Affordability by Area** - a treemap of the top 10 local authorities by transaction volume (coloured by affordability), plus a table of the 10 least affordable areas.
3. **Price & Earnings Over Time** - a local authority selector (top 10 by transaction volume), a combo chart of price vs. pay over time, and an affordability ratio trend with a national-average reference line.
4. **Local Authority Comparison** - a scatter plot of price vs. pay for the top 20 authorities by transaction volume (bubble size = transaction volume, colour = affordability ratio), plus a table of the 10 most affordable areas.
5. **Notes & Methodology** (hidden in the live file) - data sources, known limitations, and methodology notes, linked from an info button on the Overview page.

## Status

Data pipeline and dashboard are both complete. See `docs/power_bi_setup.md` for the column type corrections and null-handling approach used when importing the data into Power BI.
