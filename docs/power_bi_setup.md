# Power BI Dashboard Setup Notes

Notes on building the dashboard from `data/processed/price_vs_earnings_by_la_year.csv`,
covering steps that aren't obvious from the CSV alone.

## 1. Column data types

Power BI's default CSV import types every column as **Text**. These need
correcting in Power Query (Transform data) before building any visuals,
otherwise sorting, aggregation, and conditional formatting on numeric
columns won't work correctly:

| Column | Type | Why |
|---|---|---|
| `district`, `la_code`, `la_name` | Text | Unchanged - identifiers, not numbers |
| `year` | Whole Number | |
| `median_price`, `mean_price`, `min_price`, `max_price` | Fixed Decimal Number | Currency; Fixed Decimal avoids floating-point rounding errors that plain Decimal Number can introduce |
| `transaction_count` | Whole Number | |
| `median_pay`, `mean_pay` | Fixed Decimal Number | Currency, same reasoning as price columns |
| `number_of_jobs_thousands` | Whole Number | ONS publishes this already rounded to the nearest thousand - the raw source has no decimal places, confirmed by checking the source workbooks directly |
| `price_to_earnings_ratio` | Fixed Decimal Number | |

## 2. Nulls: kept intentionally, not filtered

`median_pay`, `mean_pay`, `number_of_jobs_thousands`, and
`price_to_earnings_ratio` contain genuine blanks where ONS suppressed the
underlying ASHE figure (see `docs/data_limitations.md` section 6). These
are **deliberately left as native Power BI blanks** - not filtered out of
the model and not imputed/estimated. Filtering them out would silently
under-represent certain local authorities (smaller/rural ones especially,
since those are the ones ASHE tends to suppress) without any indication in
the dashboard that this happened.

These aren't a required part of the dashboard - they were used once, as a
one-off sanity check, to confirm the imported row/blank counts matched the
documented figures below, then removed from the working file. Recreate
them temporarily (as Card visuals) any time you want to re-verify after a
data refresh, using this DAX:

```dax
Total Rows = COUNTROWS(price_vs_earnings_by_la_year)

Blank Median Pay Count =
COUNTROWS(FILTER(price_vs_earnings_by_la_year, ISBLANK(price_vs_earnings_by_la_year[median_pay])))

Blank Mean Pay Count =
COUNTROWS(FILTER(price_vs_earnings_by_la_year, ISBLANK(price_vs_earnings_by_la_year[mean_pay])))
```

Expected values against the current CSV: Total Rows = 3,674; Blank Median
Pay Count = 197; Blank Mean Pay Count = 93.

## 3. Handling blanks in visuals

Rather than leaving the blanks unexplained, each visual that touches these
columns should surface the gap:

- **Map**: blank `price_to_earnings_ratio` gets a distinct grey fill
  (rather than defaulting to white/transparent) plus a legend note:
  "Grey = earnings data suppressed by ONS (small sample size)."
- **Line/combo charts over time**: Power BI shows a natural gap/break at
  missing years by default - add a small caption noting this rather than
  leaving it unexplained.
- **Scatter plot**: local authority/years with a blank `mean_pay` (or
  `median_pay`, depending which axis is used) won't plot at all. A
  dynamic caption using a measure like `Scatter Plotted Count` (count of
  non-blank rows) against `Total Rows` communicates how many points are
  excluded and why.
- **Ranked table / multi-row card**: no special handling needed - blanks
  are self-evident in a table, and `AVERAGE()` already excludes blanks
  correctly for card measures.
