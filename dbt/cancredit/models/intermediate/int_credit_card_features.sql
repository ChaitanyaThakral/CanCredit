{{ config(materialized='table') }}

SELECT
    applicant_id,
    COUNT(*) AS cc_num_months,
    COALESCE(ROUND(AVG(
        amt_balance
        / NULLIF(amt_credit_limit_actual, 0)
    ), 4), 0) AS cc_avg_utilization,
    COALESCE(MAX(
        amt_balance
        / NULLIF(amt_credit_limit_actual, 0)
    ), 0) AS cc_max_utilization,
    COALESCE(AVG(amt_drawings_current), 0) AS cc_avg_monthly_drawings,
    SUM(CASE WHEN sk_dpd_def > 0 THEN 1 ELSE 0 END) AS cc_months_overdue
FROM {{ ref('stg_credit_card_balance') }}
GROUP BY applicant_id
