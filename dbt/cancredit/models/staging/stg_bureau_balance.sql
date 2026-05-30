{{ config(materialized='view') }}

SELECT
    SK_ID_BUREAU AS BUREAU_ID,
    MONTHS_BALANCE,
    STATUS,
    CURRENT_TIMESTAMP() AS DBT_LOADED_AT
FROM {{ source('raw', 'bureau_balance') }}
