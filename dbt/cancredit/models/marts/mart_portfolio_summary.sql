{{ config(materialized='table') }}

SELECT
    loan_type,
    education_level,
    credit_risk_segment,
    gender,
    income_type,
    COUNT(*)                              AS total_applications,
    SUM(default_flag)                     AS total_defaults,
    ROUND(AVG(default_flag)*100, 2)      AS default_rate_pct,
    ROUND(AVG(loan_amount), 0)           AS avg_loan_amount,
    ROUND(AVG(annual_income), 0)         AS avg_annual_income,
    ROUND(AVG(credit_to_income_ratio),3) AS avg_dti,
    ROUND(AVG(composite_risk_score), 4)  AS avg_risk_score
FROM {{ ref('mart_credit_application_fact') }}
GROUP BY 1, 2, 3, 4, 5
