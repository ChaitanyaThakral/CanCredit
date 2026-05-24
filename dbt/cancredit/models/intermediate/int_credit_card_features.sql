{{ config(materialized='table') }}

SELECT
    applicant_id,
    COUNT(*)                                                          AS cc_num_months,
    COALESCE(ROUND(AVG(AMT_BALANCE /
        NULLIF(AMT_CREDIT_LIMIT_ACTUAL, 0)), 4), 0)                 AS cc_avg_utilization,
    COALESCE(MAX(AMT_BALANCE /
        NULLIF(AMT_CREDIT_LIMIT_ACTUAL, 0)), 0)                     AS cc_max_utilization,
    COALESCE(AVG(AMT_DRAWINGS_CURRENT), 0)                          AS cc_avg_monthly_drawings,
    SUM(CASE WHEN SK_DPD_DEF > 0 THEN 1 ELSE 0 END)                AS cc_months_overdue
FROM {{ ref('stg_credit_card_balance') }}
GROUP BY applicant_id
