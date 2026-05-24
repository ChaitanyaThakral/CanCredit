{{ config(materialized='table') }}

SELECT
    applicant_id,
    COUNT(*)                                                          AS prev_num_applications,
    SUM(CASE WHEN NAME_CONTRACT_STATUS = 'Approved' THEN 1 ELSE 0 END) AS prev_approved,
    SUM(CASE WHEN NAME_CONTRACT_STATUS = 'Refused'  THEN 1 ELSE 0 END) AS prev_refused,
    ROUND(SUM(CASE WHEN NAME_CONTRACT_STATUS = 'Refused' THEN 1 ELSE 0 END)::FLOAT
          / NULLIF(COUNT(*), 0), 4)                                  AS prev_refusal_rate,
    COALESCE(AVG(AMT_CREDIT), 0)                                    AS prev_avg_credit,
    COALESCE(AVG(AMT_ANNUITY), 0)                                   AS prev_avg_annuity,
    COALESCE(AVG(DAYS_DECISION / -365.25), 0)                       AS prev_avg_decision_age_yrs
FROM {{ ref('stg_previous_application') }}
GROUP BY applicant_id
