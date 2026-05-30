-- Use a dynamic NULL profiling query across columns — demonstrates SQL maturity
SELECT
    'AMT_INCOME_TOTAL' AS col,
    COUNT(*) - COUNT(amt_income_total) AS nulls,
    ROUND((COUNT(*) - COUNT(amt_income_total))::FLOAT / COUNT(*) * 100, 1)
        AS null_pct
FROM cancredit_db.raw.application_train
UNION ALL
SELECT
    'EXT_SOURCE_1',
    COUNT(*) - COUNT(ext_source_1),
    ROUND((COUNT(*) - COUNT(ext_source_1))::FLOAT / COUNT(*) * 100, 1)
FROM cancredit_db.raw.application_train
UNION ALL
SELECT
    'EXT_SOURCE_2',
    COUNT(*) - COUNT(ext_source_2),
    ROUND((COUNT(*) - COUNT(ext_source_2))::FLOAT / COUNT(*) * 100, 1)
FROM cancredit_db.raw.application_train
UNION ALL
SELECT
    'EXT_SOURCE_3',
    COUNT(*) - COUNT(ext_source_3),
    ROUND((COUNT(*) - COUNT(ext_source_3))::FLOAT / COUNT(*) * 100, 1)
FROM cancredit_db.raw.application_train
UNION ALL
SELECT
    'OCCUPATION_TYPE',
    COUNT(*) - COUNT(occupation_type),
    ROUND((COUNT(*) - COUNT(occupation_type))::FLOAT / COUNT(*) * 100, 1)
FROM cancredit_db.raw.application_train
ORDER BY null_pct DESC;
-- EXT_SOURCE_1 is ~56% null, EXT_SOURCE_3 is ~25% null — document this for imputation decisions
