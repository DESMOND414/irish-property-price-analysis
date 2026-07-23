-- Rank counties by price growth from their first to most recent full year
-- of data, using RANK() — surfaces which counties saw the sharpest rises.

WITH yearly AS (
    SELECT
        county,
        year,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY price) AS median_price
    FROM properties
    WHERE price_outlier = FALSE
    GROUP BY county, year
),
bounds AS (
    SELECT
        county,
        MIN(year) AS first_year,
        MAX(year) AS last_year
    FROM yearly
    GROUP BY county
),
first_last AS (
    SELECT
        b.county,
        f.median_price AS first_year_median,
        l.median_price AS last_year_median
    FROM bounds b
    JOIN yearly f ON f.county = b.county AND f.year = b.first_year
    JOIN yearly l ON l.county = b.county AND l.year = b.last_year
)
SELECT
    county,
    first_year_median,
    last_year_median,
    ROUND((100.0 * (last_year_median - first_year_median) / first_year_median)::numeric, 1) AS total_pct_growth,
    RANK() OVER (ORDER BY (last_year_median - first_year_median) / first_year_median DESC) AS growth_rank
FROM first_last
ORDER BY growth_rank;
