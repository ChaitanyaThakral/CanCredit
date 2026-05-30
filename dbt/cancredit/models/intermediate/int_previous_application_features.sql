{{ config(materialized='table') }}

SELECT
    applicant_id,
    COUNT(*) AS prev_num_applications,
    SUM(CASE WHEN name_contract_status = 'Approved' THEN 1 ELSE 0 END)
        AS prev_approved,
    SUM(CASE WHEN name_contract_status = 'Refused' THEN 1 ELSE 0 END)
        AS prev_refused,
    ROUND(
        SUM(CASE WHEN name_contract_status = 'Refused' THEN 1 ELSE 0 END)::FLOAT
        / NULLIF(COUNT(*), 0), 4
    ) AS prev_refusal_rate,
    COALESCE(AVG(amt_credit), 0) AS prev_avg_credit,
    COALESCE(AVG(amt_annuity), 0) AS prev_avg_annuity,
    COALESCE(AVG(days_decision / -365.25), 0) AS prev_avg_decision_age_yrs
FROM {{ ref('stg_previous_application') }}
GROUP BY applicant_id
