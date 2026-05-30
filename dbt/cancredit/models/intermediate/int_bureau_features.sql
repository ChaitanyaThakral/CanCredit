{{ config(materialized='table') }}

WITH bureau AS (SELECT * FROM {{ ref('stg_bureau') }}),

bureau_bal AS (SELECT * FROM {{ ref('stg_bureau_balance') }})

SELECT
    b.applicant_id,
    COUNT(DISTINCT b.bureau_id) AS bureau_num_records,
    SUM(CASE WHEN b.credit_status = 'Active' THEN 1 ELSE 0 END)
        AS bureau_active_credits,
    SUM(CASE WHEN b.credit_status = 'Closed' THEN 1 ELSE 0 END)
        AS bureau_closed_credits,
    COALESCE(SUM(b.credit_sum), 0) AS bureau_total_credit,
    COALESCE(SUM(b.credit_debt), 0) AS bureau_total_debt,
    COALESCE(SUM(b.credit_overdue), 0) AS bureau_total_overdue,
    COALESCE(AVG(b.years_since_credit_start), 0) AS bureau_avg_credit_age_yrs,
    -- Worst delinquency from monthly balance history (0=ok, 1-5=late, C=closed, X=unknown)
    COALESCE(MAX(
        CASE
            WHEN bb.status IN ('1', '2', '3', '4', '5')
                THEN bb.status::INT
            ELSE 0
        END
    ), 0) AS bureau_worst_delinquency,
    -- Proportion of months in delinquency
    COALESCE(ROUND(AVG(
        CASE
            WHEN bb.status NOT IN ('0', 'X', 'C') THEN 1.0
            ELSE 0.0
        END
    ), 4), 0) AS bureau_delinquency_rate
FROM bureau AS b
LEFT JOIN bureau_bal AS bb ON b.bureau_id = bb.bureau_id
GROUP BY b.applicant_id
