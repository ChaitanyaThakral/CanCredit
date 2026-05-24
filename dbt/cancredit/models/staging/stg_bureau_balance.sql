{{ config(materialized='view') }}

SELECT
    SK_ID_BUREAU                              AS bureau_id,
    MONTHS_BALANCE                            AS months_balance,
    STATUS                                    AS status,
    CURRENT_TIMESTAMP()                       AS dbt_loaded_at
FROM {{ source('raw', 'bureau_balance') }}
