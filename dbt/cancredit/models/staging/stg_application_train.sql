{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('raw', 'application_train') }}
),

cleaned AS (
    SELECT
        sk_id_curr AS applicant_id,
        target AS default_flag,
        name_contract_type AS loan_type,
        code_gender AS gender,
        flag_own_car AS owns_car,
        flag_own_realty AS owns_realty,
        cnt_children AS num_children,
        amt_income_total AS annual_income,
        amt_credit AS loan_amount,
        amt_annuity AS loan_annuity,
        amt_goods_price AS goods_price,
        ext_source_1,
        ext_source_2,
        ext_source_3,
        name_education_type AS education_level,
        name_family_status AS family_status,
        name_housing_type AS housing_type,
        name_income_type AS income_type,
        occupation_type AS occupation,
        region_population_relative AS region_pop_pct,
        region_rating_client AS region_rating,
        flag_work_phone AS has_work_phone,
        flag_email AS has_email,
        cnt_fam_members AS family_size,
        FLOOR(ABS(days_birth) / 365.25) AS age_years,
        CASE
            WHEN days_employed = 365243 THEN NULL
            ELSE FLOOR(ABS(days_employed) / 365.25)
        END AS years_employed,
        ROUND(amt_credit / NULLIF(amt_income_total, 0), 4)
            AS credit_to_income_ratio,
        ROUND(amt_annuity / NULLIF(amt_income_total, 0), 4)
            AS annuity_to_income_ratio,
        days_registration / -365.25 AS years_since_registration,
        days_id_publish / -365.25 AS years_since_id_publish,
        CURRENT_TIMESTAMP() AS dbt_loaded_at
    FROM source
    WHERE
        sk_id_curr IS NOT NULL
        AND amt_income_total > 0
        AND amt_credit > 0
)

SELECT * FROM cleaned
QUALIFY
    ROW_NUMBER() OVER (PARTITION BY applicant_id ORDER BY dbt_loaded_at DESC)
    = 1
