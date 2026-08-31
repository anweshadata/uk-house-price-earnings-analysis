-- Median price paid per local authority (district) per year, 2015-2026.
-- SQLite has no native MEDIAN() aggregate, so this uses ROW_NUMBER()/COUNT()
-- window functions to find the middle value (or average of the two middle
-- values, for an even-sized group) within each district/year group.
--
-- Source table `price_paid` already filtered to:
--   - PPD Category Type = A (standard residential sales only)
--   - year 2015-2026
-- (see scripts/load_price_paid.py and scripts/README.md for how it was built)

WITH ranked AS (
    SELECT
        district,
        year,
        price,
        ROW_NUMBER() OVER (PARTITION BY district, year ORDER BY price) AS rn,
        COUNT(*)     OVER (PARTITION BY district, year)                AS cnt
    FROM price_paid
)
SELECT
    district,
    year,
    AVG(CASE WHEN rn IN ((cnt + 1) / 2, (cnt + 2) / 2) THEN price END) AS median_price,
    COUNT(*)                AS transaction_count,
    ROUND(AVG(price), 0)    AS mean_price,
    MIN(price)              AS min_price,
    MAX(price)              AS max_price
FROM ranked
GROUP BY district, year
ORDER BY district, year;
