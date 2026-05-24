{{ config(materialized='view') }}

SELECT
    SK_ID_CURR                                AS applicant_id,
    SK_ID_BUREAU                              AS bureau_id,
    CREDIT_ACTIVE                             AS credit_status,
    CREDIT_CURRENCY                           AS credit_currency,
    DAYS_CREDIT / -365.25                     AS years_since_credit_start,
    DAYS_CREDIT_ENDDATE / -365.25             AS years_to_credit_end,
    COALESCE(AMT_CREDIT_SUM, 0)              AS credit_sum,
    COALESCE(AMT_CREDIT_SUM_DEBT, 0)         AS credit_debt,
    COALESCE(AMT_CREDIT_SUM_OVERDUE, 0)      AS credit_overdue,
    COALESCE(AMT_CREDIT_SUM_LIMIT, 0)        AS credit_limit,
    CREDIT_TYPE                               AS credit_type,
    CURRENT_TIMESTAMP()                       AS dbt_loaded_at
FROM {{ source('raw', 'bureau') }}
WHERE SK_ID_CURR IS NOT NULL
