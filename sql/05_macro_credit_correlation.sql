-- Join application data to BOC macro rates by year to show rate environment effect on default rates
-- Canada-specific insight
WITH app_year AS (
    SELECT
        SK_ID_CURR,
        TARGET,
        YEAR(DATEADD('day', DAYS_DECISION, CURRENT_DATE)) AS application_year
    FROM CANCREDIT_DB.RAW.APPLICATION_TRAIN
    WHERE DAYS_DECISION IS NOT NULL
),
macro_annual AS (
    SELECT
        YEAR(TRY_TO_DATE(OBS_DATE)) AS yr,
        AVG(TRY_TO_NUMBER(CAOVERAGE)) AS avg_overnight_rate
    FROM CANCREDIT_DB.RAW.BOC_MACRO
    GROUP BY 1
)
SELECT
    a.application_year,
    m.avg_overnight_rate,
    COUNT(*)                    AS applications,
    ROUND(AVG(a.TARGET)*100,2) AS default_rate_pct,
    CASE WHEN m.avg_overnight_rate < 1.0 THEN 'Low Rate Era'
         WHEN m.avg_overnight_rate < 3.0 THEN 'Rising Rate Era'
         ELSE 'High Rate Era' END AS rate_environment
FROM app_year a
LEFT JOIN macro_annual m ON a.application_year = m.yr
GROUP BY 1, 2, 5
ORDER BY 1;
