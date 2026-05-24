{{ config(materialized='view') }}

SELECT
    SK_ID_PREV                                AS prev_loan_id,
    SK_ID_CURR                                AS applicant_id,
    MONTHS_BALANCE                            AS months_balance,
    AMT_BALANCE                               AS balance,
    AMT_CREDIT_LIMIT_ACTUAL                   AS credit_limit_actual,
    AMT_DRAWINGS_CURRENT                      AS drawings_current,
    AMT_PAYMENT_CURRENT                       AS payment_current,
    AMT_TOTAL_RECEIVABLE                      AS total_receivable,
    CNT_DRAWINGS_CURRENT                      AS count_drawings_current,
    NAME_CONTRACT_STATUS                      AS contract_status,
    SK_DPD                                    AS days_past_due,
    SK_DPD_DEF                                AS days_past_due_def,
    CURRENT_TIMESTAMP()                       AS dbt_loaded_at
FROM {{ source('raw', 'credit_card_balance') }}
WHERE SK_ID_CURR IS NOT NULL
