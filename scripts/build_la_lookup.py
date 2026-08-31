"""
Build a lookup mapping HM Land Registry price-paid `district` names (plain
text, no ONS code) onto ONS `la_code` (from the ASHE data), by normalising
both sides' names and matching PER YEAR (not globally). Matching per year is
required because local government reorganisation changed which LA codes and
names are valid in a given year (e.g. Buckinghamshire's four former
districts merged into one unitary authority in 2019/2020) - a name that is
ambiguous across all years combined is usually unambiguous within any single
year.

Anything that doesn't match automatically is left unmatched rather than
guessed, and written out separately so it can be resolved by hand and
reviewed, not silently dropped.
"""
import csv
import re
import sqlite3

PP_DB = "/sessions/rcw-01fsbh8r5pnyypebat41w6ee/scratch/price_paid.sqlite"  # local safe copy, not the connected mount
ASHE_CSV = "data/processed/ashe_median_pay_by_la_year.csv"
OUT_MATCHED = "/sessions/rcw-01fsbh8r5pnyypebat41w6ee/scratch/la_lookup.csv"
OUT_UNMATCHED_PP = "/sessions/rcw-01fsbh8r5pnyypebat41w6ee/scratch/la_lookup_unmatched_price_paid.csv"

# Manual aliases applied AFTER normalize(), for genuine naming differences
# between HM Land Registry's `district` field and ONS/ASHE's `la_name` that
# are not explained by local government reorganisation:
#   - WREKIN: HM Land Registry has always labelled this unitary authority's
#     price paid records "WREKIN" (never "TELFORD"), across all years
#     2015-2026 at a steady volume - this is just Land Registry's own naming
#     convention for the Telford & Wrekin UA, not a reorg artefact.
#   - RHONDDA CYNON TAFF vs TAF: genuine spelling variant between the two
#     sources (Land Registry uses double-F, ONS uses single-F).
#   - THE VALE OF GLAMORGAN vs VALE OF GLAMORGAN: leading article difference.
ALIASES = {
    "WREKIN": "TELFORD AND WREKIN",
    "RHONDDA CYNON TAFF": "RHONDDA CYNON TAF",
}


def normalize(name):
    n = name.upper().strip()
    # Welsh bilingual names in ASHE are given as "English / Welsh" (e.g.
    # "Cardiff / Caerdydd") - keep only the English part before the slash.
    n = n.split("/")[0].strip()
    n = re.sub(r"^THE\s+", "", n)
    n = re.sub(r"\bUA\b", "", n)
    n = re.sub(r"\bCITY OF\b", "", n)
    n = re.sub(r",", "", n)
    n = n.replace("&", "AND")
    n = re.sub(r"\bCOUNTY\b", "", n)
    n = re.sub(r"\bMET\b", "", n)
    n = re.sub(r"\bDISTRICT\b", "", n)
    n = re.sub(r"\bBOROUGH\b", "", n)
    n = re.sub(r"\bLONDON\b", "", n)
    n = re.sub(r"[^A-Z ]", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    n = ALIASES.get(n, n)
    return n


def main():
    conn = sqlite3.connect(PP_DB)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT district, year FROM price_paid ORDER BY district, year")
    pp_pairs = cur.fetchall()
    conn.close()

    # year -> {normalized_name: set(la_code)}
    ashe_by_year = {}
    with open(ASHE_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            y = int(row["year"])
            ashe_by_year.setdefault(y, {}).setdefault(normalize(row["la_name"]), set()).add(row["la_code"])

    matched = []
    unmatched = []
    for district, year in pp_pairs:
        norm = normalize(district)
        codes = ashe_by_year.get(year, {}).get(norm)
        if codes and len(codes) == 1:
            matched.append((district, year, norm, next(iter(codes)), "normalized_exact_per_year"))
        elif codes and len(codes) > 1:
            unmatched.append((district, year, norm, f"ambiguous: {sorted(codes)}"))
        else:
            unmatched.append((district, year, norm, "no match"))

    with open(OUT_MATCHED, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["price_paid_district", "year", "normalized_name", "la_code", "match_type"])
        w.writerows(matched)

    with open(OUT_UNMATCHED_PP, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["price_paid_district", "year", "normalized_name", "reason"])
        w.writerows(unmatched)

    total = len(pp_pairs)
    print(f"total price_paid (district, year) pairs: {total}")
    print(f"matched: {len(matched)} ({len(matched)/total:.1%})")
    print(f"unmatched: {len(unmatched)} ({len(unmatched)/total:.1%})")

    # Also report unique district-level summary: a district counts as fully
    # matched only if ALL of its years matched.
    districts = sorted(set(d for d, y in pp_pairs))
    unmatched_districts = sorted(set(d for d, y, n, r in unmatched))
    print(f"\ndistinct districts: {len(districts)}")
    print(f"districts with at least one unmatched year: {len(unmatched_districts)}")
    if unmatched_districts:
        print(unmatched_districts)


if __name__ == "__main__":
    main()
