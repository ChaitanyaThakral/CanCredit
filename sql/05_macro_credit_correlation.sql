-- Join application data to BOC macro rates by year to show rate environment effect on default rates
-- Canada-specific insight
WITH app_year AS (
    SELECT
        sk_id_curr,
        target,
        YEAR(DATEADD('day', days_decision, CURRENT_DATE)) AS application_year
    FROM cancredit_db.raw.application_train
    WHERE days_decision IS NOT NULL
),

macro_annual AS (
    SELECT
        YEAR(TRY_TO_DATE(obs_date)) AS yr,
        AVG(TRY_TO_NUMBER(caoverage)) AS avg_overnight_rate
    FROM cancredit_db.raw.boc_macro
    GROUP BY 1
)

SELECT
    a.application_year,
    m.avg_overnight_rate,
    COUNT(*) AS applications,
    ROUND(AVG(a.target) * 100, 2) AS default_rate_pct,
    CASE
        WHEN m.avg_overnight_rate < 1.0 THEN 'Low Rate Era'
        WHEN m.avg_overnight_rate < 3.0 THEN 'Rising Rate Era'
        ELSE 'High Rate Era'
    END AS rate_environment
FROM app_year AS a
LEFT JOIN macro_annual AS m ON a.application_year = m.yr
GROUP BY 1, 2, 5
ORDER BY 1;
