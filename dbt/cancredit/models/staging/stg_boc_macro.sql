{{ config(materialized='view') }}

SELECT
    OBS_DATE                                  AS obs_date,
    TRY_TO_NUMBER(CAOVERAGE)                  AS overnight_rate,
    TRY_TO_NUMBER(AUCAUSBOND2Y)               AS bond_yield_2yr,
    TRY_TO_NUMBER(AUCAUSBOND10Y)              AS bond_yield_10yr,
    TRY_TO_NUMBER(FXCADUSD)                   AS fx_cad_usd,
    TRY_TO_NUMBER(CPIALL)                     AS cpi_all,
    CURRENT_TIMESTAMP()                       AS dbt_loaded_at
FROM {{ source('raw', 'boc_macro') }}
