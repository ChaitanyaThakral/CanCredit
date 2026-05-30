-- Join installments to application to show defaulters have measurably worse payment discipline
WITH payment_stats AS (
    SELECT
        sk_id_curr,
        COUNT(*) AS total_payments,
        SUM(CASE WHEN days_entry_payment > days_instalment THEN 1 ELSE 0 END)
            AS late_payments,
        MAX(GREATEST(days_entry_payment - days_instalment, 0))
            AS worst_days_late,
        ROUND(AVG(amt_payment / NULLIF(amt_instalment, 0)), 4)
            AS avg_payment_ratio
    FROM cancredit_db.raw.installments_payments
    GROUP BY sk_id_curr
)

SELECT
    a.target,
    ROUND(AVG(
        p.late_payments::FLOAT
        / NULLIF(p.total_payments, 0)
    ) * 100, 2) AS avg_late_pmt_rate_pct,
    ROUND(AVG(p.worst_days_late), 1) AS avg_worst_days_late,
    ROUND(AVG(p.avg_payment_ratio), 4) AS avg_payment_coverage,
    COUNT(*) AS applicant_count
FROM cancredit_db.raw.application_train AS a
INNER JOIN payment_stats AS p ON a.sk_id_curr = p.sk_id_curr
GROUP BY a.target;
-- Defaulters: ~25% late rate, 50+ worst days late
-- Non-defaulters: ~8% late rate, <15 worst days late
