{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('raw', 'application_train') }}
),
cleaned AS (
    SELECT
        SK_ID_CURR                                                    AS applicant_id,
        TARGET                                                        AS default_flag,
        NAME_CONTRACT_TYPE                                            AS loan_type,
        CODE_GENDER                                                   AS gender,
        FLAG_OWN_CAR                                                  AS owns_car,
        FLAG_OWN_REALTY                                               AS owns_realty,
        CNT_CHILDREN                                                  AS num_children,
        AMT_INCOME_TOTAL                                              AS annual_income,
        AMT_CREDIT                                                    AS loan_amount,
        AMT_ANNUITY                                                   AS loan_annuity,
        AMT_GOODS_PRICE                                               AS goods_price,
        FLOOR(ABS(DAYS_BIRTH) / 365.25)                              AS age_years,
        CASE WHEN DAYS_EMPLOYED = 365243 THEN NULL
             ELSE FLOOR(ABS(DAYS_EMPLOYED) / 365.25)
        END                                                           AS years_employed,
        ROUND(AMT_CREDIT / NULLIF(AMT_INCOME_TOTAL, 0), 4)          AS credit_to_income_ratio,
        ROUND(AMT_ANNUITY / NULLIF(AMT_INCOME_TOTAL, 0), 4)         AS annuity_to_income_ratio,
        EXT_SOURCE_1,
        EXT_SOURCE_2,
        EXT_SOURCE_3,
        NAME_EDUCATION_TYPE                                           AS education_level,
        NAME_FAMILY_STATUS                                            AS family_status,
        NAME_HOUSING_TYPE                                             AS housing_type,
        NAME_INCOME_TYPE                                              AS income_type,
        OCCUPATION_TYPE                                               AS occupation,
        REGION_POPULATION_RELATIVE                                    AS region_pop_pct,
        REGION_RATING_CLIENT                                          AS region_rating,
        FLAG_WORK_PHONE                                               AS has_work_phone,
        FLAG_EMAIL                                                    AS has_email,
        CNT_FAM_MEMBERS                                               AS family_size,
        DAYS_REGISTRATION / -365.25                                   AS years_since_registration,
        DAYS_ID_PUBLISH / -365.25                                     AS years_since_id_publish,
        CURRENT_TIMESTAMP()                                           AS dbt_loaded_at
    FROM source
    WHERE SK_ID_CURR IS NOT NULL
      AND AMT_INCOME_TOTAL > 0
      AND AMT_CREDIT > 0
)
SELECT * FROM cleaned
QUALIFY ROW_NUMBER() OVER (PARTITION BY applicant_id ORDER BY dbt_loaded_at DESC) = 1
