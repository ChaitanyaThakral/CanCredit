{{ config(materialized='view') }}

SELECT
    SK_ID_PREV                                AS prev_loan_id,
    SK_ID_CURR                                AS applicant_id,
    NAME_CONTRACT_TYPE                        AS loan_type,
    AMT_ANNUITY                               AS annuity,
    AMT_APPLICATION                           AS amount_applied,
    AMT_CREDIT                                AS amount_credited,
    AMT_DOWN_PAYMENT                          AS down_payment,
    AMT_GOODS_PRICE                           AS goods_price,
    NAME_CONTRACT_STATUS                      AS contract_status,
    DAYS_DECISION / -365.25                   AS years_since_decision,
    NAME_PAYMENT_TYPE                         AS payment_type,
    CODE_REJECT_REASON                        AS reject_reason,
    NAME_CLIENT_TYPE                          AS client_type,
    NAME_PORTFOLIO                            AS portfolio,
    NAME_PRODUCT_TYPE                         AS product_type,
    CHANNEL_TYPE                              AS channel_type,
    NAME_YIELD_GROUP                          AS yield_group,
    CURRENT_TIMESTAMP()                       AS dbt_loaded_at
FROM {{ source('raw', 'previous_application') }}
WHERE SK_ID_CURR IS NOT NULL
