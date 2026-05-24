{{ config(materialized='table') }}

SELECT
    applicant_id,
    COUNT(*)                                                          AS inst_num_payments,
    SUM(CASE WHEN is_late THEN 1 ELSE 0 END)                        AS inst_late_count,
    ROUND(SUM(CASE WHEN is_late THEN 1 ELSE 0 END)::FLOAT
          / NULLIF(COUNT(*), 0), 4)                                  AS inst_late_rate,
    COALESCE(MAX(days_late), 0)                                      AS inst_max_days_late,
    COALESCE(AVG(days_late), 0)                                      AS inst_avg_days_late,
    COALESCE(AVG(payment_ratio), 1.0)                               AS inst_avg_payment_ratio,
    -- Total underpayment amount
    COALESCE(SUM(CASE WHEN amount_paid < amount_due
                 THEN amount_due - amount_paid ELSE 0 END), 0)       AS inst_total_underpaid
FROM {{ ref('stg_installments_payments') }}
GROUP BY applicant_id
