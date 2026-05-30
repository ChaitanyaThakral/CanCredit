-- Join bureau data to application data and rank applicants by debt-to-income decile
-- to show how bureau debt load predicts default
WITH bureau_agg AS (
    SELECT
        sk_id_curr,
        COUNT(*) AS num_bureau_records,
        SUM(CASE WHEN credit_active = 'Active' THEN 1 ELSE 0 END)
            AS active_credits,
        COALESCE(SUM(amt_credit_sum_debt), 0) AS total_bureau_debt,
        COALESCE(SUM(amt_credit_sum_overdue), 0) AS total_overdue,
        MAX(CASE
            WHEN credit_active = 'Active'
                THEN amt_credit_sum_debt
            ELSE 0
        END) AS max_active_debt
    FROM cancredit_db.raw.bureau
    GROUP BY sk_id_curr
),

enriched AS (
    SELECT
        a.sk_id_curr,
        a.target,
        a.amt_income_total,
        b.total_bureau_debt,
        b.total_overdue,
        ROUND(b.total_bureau_debt / NULLIF(a.amt_income_total, 0), 4)
            AS bureau_dti,
        NTILE(10) OVER (
            ORDER BY
                b.total_bureau_debt / NULLIF(a.amt_income_total, 0)
        ) AS dti_decile
    FROM cancredit_db.raw.application_train AS a
    INNER JOIN bureau_agg AS b ON a.sk_id_curr = b.sk_id_curr
)

SELECT
    dti_decile,
    COUNT(*) AS applicants,
    ROUND(AVG(target) * 100, 2) AS default_rate_pct,
    ROUND(AVG(total_bureau_debt), 0) AS avg_bureau_debt,
    ROUND(AVG(total_overdue), 2) AS avg_overdue_amt
FROM enriched
GROUP BY dti_decile
ORDER BY dti_decile;
-- Expected: decile 10 (highest DTI) has 2–3x the default rate of decile 1
