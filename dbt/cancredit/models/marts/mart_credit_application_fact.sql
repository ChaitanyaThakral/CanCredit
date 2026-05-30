{{ config(
    materialized='table',
    cluster_by=['credit_risk_segment', 'default_flag']
) }}

WITH app AS (SELECT * FROM {{ ref('stg_application_train') }}),

bur AS (SELECT * FROM {{ ref('int_bureau_features') }}),

inst AS (SELECT * FROM {{ ref('int_installment_features') }}),

cc AS (SELECT * FROM {{ ref('int_credit_card_features') }}),

prev AS (SELECT * FROM {{ ref('int_previous_application_features') }})

SELECT
    -- Identity
    a.applicant_id,
    a.default_flag,

    -- Application attributes
    a.loan_type,
    a.gender,
    a.age_years,
    a.years_employed,
    a.loan_amount,
    a.annual_income,
    a.credit_to_income_ratio,
    a.annuity_to_income_ratio,
    a.education_level,
    a.family_status,
    a.housing_type,
    a.income_type,
    a.num_children,
    a.region_rating,

    -- External risk scores (most predictive features)
    a.ext_source_1,
    a.ext_source_2,
    a.ext_source_3,

    -- Bureau features (COALESCE: applicants with no bureau history get 0)
    COALESCE(bur.bureau_active_credits, 0) AS bureau_active_credits,
    COALESCE(bur.bureau_total_debt, 0) AS bureau_total_debt,
    COALESCE(bur.bureau_total_overdue, 0) AS bureau_total_overdue,
    COALESCE(bur.bureau_delinquency_rate, 0) AS bureau_delinquency_rate,
    COALESCE(bur.bureau_worst_delinquency, 0) AS bureau_worst_delinquency,
    COALESCE(bur.bureau_num_records, 0) AS bureau_num_records,

    -- Installment payment behaviour
    COALESCE(inst.inst_late_rate, 0) AS inst_late_rate,
    COALESCE(inst.inst_max_days_late, 0) AS inst_max_days_late,
    COALESCE(inst.inst_avg_payment_ratio, 1.0) AS inst_avg_payment_ratio,
    COALESCE(inst.inst_total_underpaid, 0) AS inst_total_underpaid,

    -- Credit card behaviour
    COALESCE(cc.cc_avg_utilization, 0) AS cc_avg_utilization,
    COALESCE(cc.cc_max_utilization, 0) AS cc_max_utilization,
    COALESCE(cc.cc_months_overdue, 0) AS cc_months_overdue,

    -- Previous application history
    COALESCE(prev.prev_num_applications, 0) AS prev_num_applications,
    COALESCE(prev.prev_refusal_rate, 0) AS prev_refusal_rate,
    COALESCE(prev.prev_approved, 0) AS prev_approved,

    -- Derived risk segmentation (DA/BA talking point)
    CASE
        WHEN a.credit_to_income_ratio > 5 THEN 'VERY_HIGH'
        WHEN a.credit_to_income_ratio > 3 THEN 'HIGH'
        WHEN a.credit_to_income_ratio > 1.5 THEN 'MEDIUM'
        ELSE 'LOW'
    END AS credit_risk_segment,

    -- Overall risk score (simple weighted composite — discussed in interviews)
    ROUND(
        0.30 * COALESCE(bur.bureau_delinquency_rate, 0)
        + 0.25 * COALESCE(inst.inst_late_rate, 0)
        + 0.20 * LEAST(a.credit_to_income_ratio / 10.0, 1.0)
        + 0.15 * COALESCE(cc.cc_avg_utilization / 3.0, 0)
        + 0.10 * COALESCE(prev.prev_refusal_rate, 0),
        4
    ) AS composite_risk_score,

    CURRENT_TIMESTAMP() AS dbt_updated_at
FROM app AS a
LEFT JOIN bur ON a.applicant_id = bur.applicant_id
LEFT JOIN inst ON a.applicant_id = inst.applicant_id
LEFT JOIN cc ON a.applicant_id = cc.applicant_id
LEFT JOIN prev ON a.applicant_id = prev.applicant_id
