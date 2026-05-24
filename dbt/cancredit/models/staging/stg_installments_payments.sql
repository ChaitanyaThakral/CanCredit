{{ config(materialized='view') }}

SELECT
    SK_ID_CURR                                                        AS applicant_id,
    SK_ID_PREV                                                        AS prev_loan_id,
    NUM_INSTALMENT_VERSION                                            AS instalment_version,
    NUM_INSTALMENT_NUMBER                                             AS instalment_number,
    DAYS_INSTALMENT                                                   AS days_instalment,
    DAYS_ENTRY_PAYMENT                                                AS days_payment_made,
    AMT_INSTALMENT                                                    AS amount_due,
    AMT_PAYMENT                                                       AS amount_paid,
    GREATEST(DAYS_ENTRY_PAYMENT - DAYS_INSTALMENT, 0)                AS days_late,
    CASE WHEN DAYS_ENTRY_PAYMENT > DAYS_INSTALMENT THEN TRUE
         ELSE FALSE END                                               AS is_late,
    ROUND(AMT_PAYMENT / NULLIF(AMT_INSTALMENT, 0), 4)               AS payment_ratio,
    CURRENT_TIMESTAMP()                                               AS dbt_loaded_at
FROM {{ source('raw', 'installments_payments') }}
WHERE SK_ID_CURR IS NOT NULL
