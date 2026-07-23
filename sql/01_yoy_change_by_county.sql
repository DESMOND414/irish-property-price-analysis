-- Year-over-year % change in median sale price, per county.
-- Uses a CTE to pre-aggregate to one row per (county, year), then a window
-- function (LAG) to compare each year against the previous one.

WITH yearly AS (
    SELECT
        county,
        year,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY price) AS median_price,
        COUNT(*) AS n_sales
    FROM properties
    WHERE price_outlier = FALSE
    GROUP BY county, year
)
SELECT
    county,
    year,
    median_price,
    n_sales,
    LAG(median_price) OVER (PARTITION BY county ORDER BY year) AS prev_year_median,
    ROUND(
        (100.0 * (median_price - LAG(median_price) OVER (PARTITION BY county ORDER BY year))
        / NULLIF(LAG(median_price) OVER (PARTITION BY county ORDER BY year), 0))::numeric,
        1
    ) AS yoy_pct_change
FROM yearly
ORDER BY county, year;
