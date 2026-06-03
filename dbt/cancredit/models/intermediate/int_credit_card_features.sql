{{ config(materialized='table') }}

SELECT
    APPLICANT_ID,
    COUNT(*) AS cc_num_months,
    COALESCE(ROUND(AVG(
        BALANCE
        / NULLIF(CREDIT_LIMIT_ACTUAL, 0)
    ), 4), 0) AS cc_avg_utilization,
    COALESCE(MAX(
        BALANCE
        / NULLIF(CREDIT_LIMIT_ACTUAL, 0)
    ), 0) AS cc_max_utilization,
    COALESCE(AVG(DRAWINGS_CURRENT), 0) AS cc_avg_monthly_drawings,
    SUM(CASE WHEN DAYS_PAST_DUE_DEF > 0 THEN 1 ELSE 0 END) AS cc_months_overdue
FROM {{ ref('stg_credit_card_balance') }}
GROUP BY APPLICANT_ID
