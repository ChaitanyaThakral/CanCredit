{{ config(materialized='view') }}

SELECT
    SK_ID_PREV                                AS prev_loan_id,
    SK_ID_CURR                                AS applicant_id,
    MONTHS_BALANCE                            AS months_balance,
    CNT_INSTALMENT                            AS count_instalment,
    CNT_INSTALMENT_FUTURE                     AS count_instalment_future,
    NAME_CONTRACT_STATUS                      AS contract_status,
    SK_DPD                                    AS days_past_due,
    SK_DPD_DEF                                AS days_past_due_def,
    CURRENT_TIMESTAMP()                       AS dbt_loaded_at
FROM {{ source('raw', 'pos_cash_balance') }}
WHERE SK_ID_CURR IS NOT NULL
