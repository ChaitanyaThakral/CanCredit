{{ config(schema='ml_features', materialized='table') }}

SELECT
    applicant_id,
    default_flag                                         AS label,
    COALESCE(ext_source_1,    0.5)                      AS ext_source_1,
    COALESCE(ext_source_2,    0.5)                      AS ext_source_2,
    COALESCE(ext_source_3,    0.5)                      AS ext_source_3,
    credit_to_income_ratio,
    annuity_to_income_ratio,
    bureau_delinquency_rate,
    bureau_worst_delinquency,
    bureau_total_overdue,
    inst_late_rate,
    inst_max_days_late,
    inst_avg_payment_ratio,
    cc_avg_utilization,
    cc_months_overdue,
    prev_refusal_rate,
    prev_num_applications,
    age_years,
    COALESCE(years_employed,  0)                        AS years_employed,
    composite_risk_score
FROM {{ ref('mart_credit_application_fact') }}
WHERE default_flag IS NOT NULL   -- training set only (application_train, not test)
