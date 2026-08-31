"""
Build the final joined table: median house price vs. median annual pay,
per local authority (district) per year, with a price-to-earnings ratio.

Joins:
  data/processed/median_price_by_la_year.csv   (district, year -> price stats)
  data/processed/la_lookup_new.csv             (district, year -> la_code)
  data/processed/ashe_median_pay_by_la_year.csv (la_code, year -> pay stats)

Rows where the district/year pair has no la_code match (see
la_lookup_unmatched_price_paid_new.csv) are excluded, since there is no
earnings figure to join against - see docs/data_limitations.md for why.
Rows where ASHE itself suppressed the median pay for that la_code/year are
kept but with a blank earnings/ratio (also documented).
"""
import csv

PRICE_CSV = "data/processed/median_price_by_la_year.csv"
LOOKUP_CSV = "data/processed/la_lookup_new.csv"
ASHE_CSV = "data/processed/ashe_median_pay_by_la_year.csv"
OUT_CSV = "/sessions/rcw-01fsbh8r5pnyypebat41w6ee/scratch/price_vs_earnings_by_la_year.csv"


def main():
    # (district, year) -> la_code
    lookup = {}
    with open(LOOKUP_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            lookup[(row["price_paid_district"], row["year"])] = row["la_code"]

    # (la_code, year) -> {median_pay, mean_pay, number_of_jobs_thousands, la_name}
    ashe = {}
    with open(ASHE_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ashe[(row["la_code"], row["year"])] = row

    out_rows = []
    matched_price_rows = 0
    excluded_no_lookup = 0
    included_suppressed_pay = 0

    with open(PRICE_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            district, year = row["district"], row["year"]
            la_code = lookup.get((district, year))
            if la_code is None:
                excluded_no_lookup += 1
                continue

            ashe_row = ashe.get((la_code, year))
            if ashe_row is None:
                # la_code matched but ASHE has no row at all for that year
                # (shouldn't normally happen since lookup is built from ASHE
                # itself, but guard anyway)
                excluded_no_lookup += 1
                continue

            median_pay = ashe_row["median_pay"]
            ratio = ""
            if median_pay not in ("", None):
                try:
                    ratio = round(float(row["median_price"]) / float(median_pay), 2)
                except (ValueError, ZeroDivisionError):
                    ratio = ""
            else:
                included_suppressed_pay += 1

            matched_price_rows += 1
            out_rows.append({
                "district": district,
                "la_code": la_code,
                "la_name": ashe_row["la_name"],
                "year": year,
                "median_price": row["median_price"],
                "mean_price": row["mean_price"],
                "min_price": row["min_price"],
                "max_price": row["max_price"],
                "transaction_count": row["transaction_count"],
                "median_pay": median_pay,
                "mean_pay": ashe_row["mean_pay"],
                "number_of_jobs_thousands": ashe_row["number_of_jobs_thousands"],
                "price_to_earnings_ratio": ratio,
            })

    fieldnames = ["district", "la_code", "la_name", "year", "median_price",
                  "mean_price", "min_price", "max_price", "transaction_count",
                  "median_pay", "mean_pay", "number_of_jobs_thousands",
                  "price_to_earnings_ratio"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)

    print(f"joined rows written: {len(out_rows)}")
    print(f"excluded (no la_code match for that district/year): {excluded_no_lookup}")
    print(f"included but with blank pay/ratio (ASHE suppressed): {included_suppressed_pay}")


if __name__ == "__main__":
    main()
