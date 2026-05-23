-- PIVOT on EXT_SOURCE_2 deciles vs education level to show how third-party risk scores interact with demographics
-- Direct Power BI pre-computation
SELECT
    NAME_EDUCATION_TYPE,
    NTILE(5) OVER (ORDER BY EXT_SOURCE_2) AS ext2_quintile,
    COUNT(*)                              AS applicants,
    ROUND(AVG(TARGET)*100, 2)            AS default_rate_pct,
    ROUND(AVG(EXT_SOURCE_2), 4)          AS avg_ext_score_2
FROM CANCREDIT_DB.RAW.APPLICATION_TRAIN
WHERE EXT_SOURCE_2 IS NOT NULL
GROUP BY 1, 2
ORDER BY 1, 2;
