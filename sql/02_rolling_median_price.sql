-- Rolling 4-quarter median price per county, using a window frame
-- (ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) rather than a self-join —
-- the standard way to express a trailing window in SQL.

WITH quarterly AS (
    SELECT
        county,
        quarter,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY price) AS median_price
    FROM properties
    WHERE price_outlier = FALSE
    GROUP BY county, quarter
)
SELECT
    county,
    quarter,
    median_price,
    ROUND(
        AVG(median_price) OVER (
            PARTITION BY county
            ORDER BY quarter
            ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
        )::numeric,
        0
    ) AS rolling_4q_median
FROM quarterly
ORDER BY county, quarter;
