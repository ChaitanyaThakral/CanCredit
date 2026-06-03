{{ config(materialized='table') }}

SELECT
    APPLICANT_ID,
    COUNT(*) AS prev_num_applications,
    SUM(CASE WHEN CONTRACT_STATUS = 'Approved' THEN 1 ELSE 0 END)
        AS prev_approved,
    SUM(CASE WHEN CONTRACT_STATUS = 'Refused' THEN 1 ELSE 0 END)
        AS prev_refused,
    ROUND(
        SUM(CASE WHEN CONTRACT_STATUS = 'Refused' THEN 1 ELSE 0 END)::FLOAT
        / NULLIF(COUNT(*), 0), 4
    ) AS prev_refusal_rate,
    COALESCE(AVG(AMOUNT_CREDITED), 0) AS prev_avg_credit,
    COALESCE(AVG(ANNUITY), 0) AS prev_avg_annuity,
    COALESCE(AVG(YEARS_SINCE_DECISION), 0) AS prev_avg_decision_age_yrs
FROM {{ ref('stg_previous_application') }}
GROUP BY APPLICANT_ID
