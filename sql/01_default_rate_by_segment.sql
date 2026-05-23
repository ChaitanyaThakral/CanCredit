-- The core business question: which applicant segments default most? 
-- This single query becomes your primary DA interview talking point.
WITH segments AS (
    SELECT
        SK_ID_CURR,
        TARGET,
        AMT_CREDIT,
        AMT_INCOME_TOTAL,
        NAME_CONTRACT_TYPE,
        FLOOR(ABS(DAYS_BIRTH) / 365.25)                          AS age_years,
        ROUND(AMT_CREDIT / NULLIF(AMT_INCOME_TOTAL, 0), 2)       AS dti_ratio,
        CASE
            WHEN AMT_INCOME_TOTAL < 90000  THEN '1_Low (<90K)'
            WHEN AMT_INCOME_TOTAL < 180000 THEN '2_Mid (90–180K)'
            WHEN AMT_INCOME_TOTAL < 360000 THEN '3_High (180–360K)'
            ELSE '4_VeryHigh (360K+)'
        END AS income_bracket,
        CASE
            WHEN FLOOR(ABS(DAYS_BIRTH) / 365.25) < 30 THEN 'Under 30'
            WHEN FLOOR(ABS(DAYS_BIRTH) / 365.25) < 45 THEN '30–44'
            WHEN FLOOR(ABS(DAYS_BIRTH) / 365.25) < 60 THEN '45–59'
            ELSE '60+'
        END AS age_band
    FROM CANCREDIT_DB.RAW.APPLICATION_TRAIN
    WHERE AMT_INCOME_TOTAL > 0
)
SELECT
    income_bracket,
    age_band,
    NAME_CONTRACT_TYPE,
    COUNT(*)                                              AS total_applications,
    SUM(TARGET)                                           AS total_defaults,
    ROUND(AVG(TARGET) * 100, 2)                          AS default_rate_pct,
    ROUND(AVG(AMT_CREDIT), 0)                            AS avg_loan_amount,
    ROUND(AVG(dti_ratio), 3)                             AS avg_dti_ratio
FROM segments
GROUP BY 1, 2, 3
ORDER BY default_rate_pct DESC;
