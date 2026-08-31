# Data Limitations and Methodology Notes

This document records the real, verified data-quality issues and methodology
choices behind `data/processed/price_vs_earnings_by_la_year.csv`, the joined
house-price-vs-earnings table used in this project. It exists so anyone
using the output understands exactly what it does and
does not cover, rather than treating the numbers as unqualified fact.

## 1. Data sources

- **House prices**: HM Land Registry Price Paid Data, `pp-complete.csv`
  (the single complete file). Filtered to PPD Category Type **A**
  (standard price paid entries; excludes repossessions, buy-to-lets,
  and other "additional" transaction types that Land Registry itself
  flags as less reliable for typical market price) and years **2015-2026**.
  Source: https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads
- **Earnings**: ONS Annual Survey of Hours and Earnings (ASHE), **Table
  8.7a**, "Annual pay - Gross", sheet **"All"** (all employee jobs,
  full-time and part-time combined), **place of residence** basis (not
  place of work). This matches the geography basis used in ONS's own
  standard housing affordability ratio publication, which is why it was
  chosen over Table 8's other splits (male/female, full-time/part-time).
  Source: https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/earningsandworkinghours

## 2. Why median, not mean

Median price and median pay are used for the price-to-earnings ratio
because house prices and earnings are both right-skewed (a small number of
very high sale prices or very high earners pull the mean upward). ASHE
itself recommends the median for this reason. Mean values are also kept in
the output columns for reference.

## 3. Coverage gap: 2026 has no earnings data

ASHE 2026 has not been published yet (ASHE results for a given year are
typically released in the autumn of that year, based on an April survey
reference date). All price_paid rows for 2026 (**318 district/year
combinations**, all 361 districts, since 2026 registrations are already
partial for other reasons - see 3a) are excluded from the joined table for
lack of a matching earnings figure. This is an expected, dated gap, not a
data error.

### 3a. 2026 is also a partial year for house prices

Land Registry registrations lag the actual completion date, sometimes by
several months, so the 2026 price_paid figures reflect only the
transactions registered so far and will keep growing if the source file is
re-downloaded later in the year. Any 2026 figures pulled from
`price_paid.sqlite` before the join (e.g. transaction counts) should be
read as provisional for this reason, independent of the ASHE join issue.

## 4. Local government reorganisation (LGR): why 125 more district/year combinations don't match

Beyond the 2026 gap, **125 district/year combinations** (across 51 distinct
district names, all pre-2024) have no earnings match. Every one of these is
explained by genuine local government reorganisation, not a data or
matching error - confirmed by checking each case against ONS's published
change log. Two different LGR patterns show up:

**Pattern A - the new unitary authority was reorganised effective partway
through the ASHE series, and ASHE assigns each year to whichever
authority structure was in force that year, while HM Land Registry's
`district` field has been retrospectively updated to reflect the *current*
authority for all historical rows.** This means, for years before a
reorganisation, price_paid already shows the *new* post-reorg name (which
ASHE hasn't caught up to yet for those years), and for a transition window
around the reorg date, price_paid can show either name depending on when
that specific row was registered/updated. Confirmed examples:

| New authority (price_paid uses this name) | Formed | Former districts (ASHE uses these names for the years before/around the change) |
|---|---|---|
| Buckinghamshire | Apr 2020 | Aylesbury Vale, Chiltern, South Bucks, Wycombe |
| Dorset (UA) | Apr 2019 | East Dorset, North Dorset, Purbeck, West Dorset, Weymouth and Portland (and pre-2019 Poole/Bournemouth/Christchurch, later merged separately into BCP) |
| Bournemouth, Christchurch and Poole | Apr 2019 | Bournemouth, Christchurch, Poole |
| North Northamptonshire | Apr 2021 | Corby, East Northamptonshire, Kettering, Wellingborough |
| West Northamptonshire | Apr 2021 | Daventry, Northampton, South Northamptonshire |
| Somerset (UA) | Apr 2023 | Mendip, Sedgemoor, South Somerset, Somerset West and Taunton |
| Somerset West and Taunton | Apr 2019 | Taunton Deane, West Somerset |
| East Suffolk | Apr 2019 | Suffolk Coastal, Waveney |
| West Suffolk | Apr 2019 | Forest Heath, St Edmundsbury |
| North Yorkshire (UA) | Apr 2023 | Craven, Hambleton, Harrogate, Richmondshire, Ryedale, Scarborough, Selby |
| Cumberland | Apr 2023 | Allerdale, Carlisle, Copeland |
| Westmorland and Furness | Apr 2023 | Barrow-in-Furness, Eden, South Lakeland |
| Folkestone and Hythe | 2018 (renamed from Shepway) | Shepway |

**Pattern B - a boundary change did not occur, only the ONS geography
code was reissued** (Barnsley and Sheffield in 2024, and similar ONS
administrative code refreshes). These didn't surface as name mismatches
here because the *name* stayed the same across the reissue and the fix in
section 5 already matches on name per year; they were investigated
separately during development and are noted here for completeness.

**These 125 rows are correctly excluded, not a bug.** Forcing a match
across a genuine reorganisation would mean either attributing pre-reform
earnings to a local authority that didn't yet exist in that form, or
splitting a merged authority's post-reform earnings figure across its
former parts with no principled way to do so. Leaving them out is the more
honest choice; a reader wanting continuous series for these areas would
need to build their own aggregation/allocation rule and document its
assumptions.

## 5. Matching HM Land Registry `district` names to ONS `la_code`

`scripts/build_la_lookup.py` matches on normalised name **per (district,
year) pair**, not globally across all years. This matters because the same
plain-text name can map to different `la_code`s depending on the year (the
reorganisation cases above), so a global match either produces false
ambiguity (multiple codes competing for one name) or a wrong static
mapping. Matching per year resolved all 6 cases that were ambiguous under
a global match (Barnsley, Buckinghamshire, Dorset, North Yorkshire,
Sheffield, Somerset).

Two further, non-reorg-related name differences were also handled
explicitly:

- **Welsh bilingual names**: ASHE gives Welsh local authorities as
  `"English name / Welsh name"` (e.g. `"Cardiff / Caerdydd"`); the
  normaliser keeps only the English part before matching.
- **Spelling/wording variants**: `"Rhondda Cynon Taff"` (price_paid,
  double-F) vs `"Rhondda Cynon Taf"` (ASHE, single-F); `"The Vale of
  Glamorgan"` (price_paid) vs `"Vale of Glamorgan"` (ASHE) - resolved with
  an explicit alias and a leading-"THE" strip respectively.
- **"Wrekin"**: HM Land Registry labels this unitary authority's price
  paid records `"WREKIN"` in every year 2015-2026 (never "Telford"), at a
  steady volume (~2,300-3,500 transactions/year) consistent with covering
  the whole authority - this is simply Land Registry's own naming
  convention for the Telford & Wrekin unitary authority, not a
  reorganisation artefact. Handled with a manual alias to
  `"Telford and Wrekin"` (ASHE's name).

After these fixes: **3,674 of 4,117** district/year combinations
(89.2%) matched to an `la_code`, with the remaining 443 fully accounted
for by section 3 (318, the 2026 coverage gap) and section 4 (125, genuine
LGR). No case was force-matched or guessed.

## 6. ASHE suppression

ASHE suppresses (`'x'` in the source spreadsheets, read here as blank/NaN)
median or mean pay figures where the underlying sample size for a local
authority/year is too small for a reliable estimate, or for disclosure
control. In the combined ASHE extract this affects **197 of 3,917 rows
(5.0%)**. These rows are kept in the joined table with a blank
`median_pay`/`price_to_earnings_ratio` rather than dropped, so the price
data for that district/year is still usable even though no ratio can be
computed. Do not fill these blanks with an interpolated or estimated
value without clearly labelling it as an estimate.

## 7. What "district" means here

Price Paid Data's `district` field is Land Registry's own administrative
label and is not always identical to an ONS local authority area (see the
Wrekin case above). For the vast majority of England and Wales it lines up
one-to-one with the ONS local authority district/unitary authority, which
is what makes this join possible at all; this document exists to be
explicit about the places where it doesn't.

## 8. Summary of row counts

| Stage | Rows |
|---|---|
| price_paid (category A, 2015-2026) | 9,760,341 transactions |
| median_price_by_la_year.csv | 4,117 (district, year) rows |
| ashe_median_pay_by_la_year.csv | 3,917 (la_code, year) rows, 2015-2025, 389 la_codes |
| la_lookup_new.csv (matched) | 3,674 (district, year) → la_code rows |
| la_lookup_unmatched_price_paid_new.csv | 443 unmatched (318 = 2026 gap, 125 = LGR) |
| price_vs_earnings_by_la_year.csv (final joined table) | 3,674 rows, of which 197 have a blank ratio (ASHE suppression) |
