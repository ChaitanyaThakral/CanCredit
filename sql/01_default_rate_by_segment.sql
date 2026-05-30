-- The core business question: which applicant segments default most?
-- This single query becomes your primary DA interview talking point.
WITH segments AS (
    SELECT
        sk_id_curr,
        target,
        amt_credit,
        amt_income_total,
        name_contract_type,
        FLOOR(ABS(days_birth) / 365.25) AS age_years,
        ROUND(amt_credit / NULLIF(amt_income_total, 0), 2) AS dti_ratio,
        CASE
            WHEN amt_income_total < 90000 THEN '1_Low (<90K)'
            WHEN amt_income_total < 180000 THEN '2_Mid (90–180K)'
            WHEN amt_income_total < 360000 THEN '3_High (180–360K)'
            ELSE '4_VeryHigh (360K+)'
        END AS income_bracket,
        CASE
            WHEN FLOOR(ABS(days_birth) / 365.25) < 30 THEN 'Under 30'
            WHEN FLOOR(ABS(days_birth) / 365.25) < 45 THEN '30–44'
            WHEN FLOOR(ABS(days_birth) / 365.25) < 60 THEN '45–59'
            ELSE '60+'
        END AS age_band
    FROM cancredit_db.raw.application_train
    WHERE amt_income_total > 0
)

SELECT
    income_bracket,
    age_band,
    name_contract_type,
    COUNT(*) AS total_applications,
    SUM(target) AS total_defaults,
    ROUND(AVG(target) * 100, 2) AS default_rate_pct,
    ROUND(AVG(amt_credit), 0) AS avg_loan_amount,
    ROUND(AVG(dti_ratio), 3) AS avg_dti_ratio
FROM segments
GROUP BY 1, 2, 3
ORDER BY default_rate_pct DESC;
