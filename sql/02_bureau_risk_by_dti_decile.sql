-- Join bureau data to application data and rank applicants by debt-to-income decile 
-- to show how bureau debt load predicts default
WITH bureau_agg AS (
    SELECT
        SK_ID_CURR,
        COUNT(*)                                              AS num_bureau_records,
        SUM(CASE WHEN CREDIT_ACTIVE = 'Active' THEN 1 ELSE 0 END) AS active_credits,
        COALESCE(SUM(AMT_CREDIT_SUM_DEBT), 0)               AS total_bureau_debt,
        COALESCE(SUM(AMT_CREDIT_SUM_OVERDUE), 0)            AS total_overdue,
        MAX(CASE WHEN CREDIT_ACTIVE = 'Active'
                 THEN AMT_CREDIT_SUM_DEBT ELSE 0 END)        AS max_active_debt
    FROM CANCREDIT_DB.RAW.BUREAU
    GROUP BY SK_ID_CURR
),
enriched AS (
    SELECT
        a.SK_ID_CURR,
        a.TARGET,
        a.AMT_INCOME_TOTAL,
        b.total_bureau_debt,
        b.total_overdue,
        ROUND(b.total_bureau_debt / NULLIF(a.AMT_INCOME_TOTAL, 0), 4) AS bureau_dti,
        NTILE(10) OVER (ORDER BY
            b.total_bureau_debt / NULLIF(a.AMT_INCOME_TOTAL, 0)) AS dti_decile
    FROM CANCREDIT_DB.RAW.APPLICATION_TRAIN a
    JOIN bureau_agg b ON a.SK_ID_CURR = b.SK_ID_CURR
)
SELECT
    dti_decile,
    COUNT(*)                          AS applicants,
    ROUND(AVG(TARGET) * 100, 2)      AS default_rate_pct,
    ROUND(AVG(total_bureau_debt), 0) AS avg_bureau_debt,
    ROUND(AVG(total_overdue), 2)     AS avg_overdue_amt
FROM enriched
GROUP BY dti_decile
ORDER BY dti_decile;
-- Expected: decile 10 (highest DTI) has 2–3x the default rate of decile 1
