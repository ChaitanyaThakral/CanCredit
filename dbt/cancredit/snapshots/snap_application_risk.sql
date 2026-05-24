{% snapshot snap_application_risk %}

{{ config(
    target_schema='SNAPSHOTS',
    unique_key='applicant_id',
    strategy='check',
    check_cols=['credit_risk_segment', 'composite_risk_score']
) }}

SELECT applicant_id, credit_risk_segment, composite_risk_score, dbt_updated_at
FROM {{ ref('mart_credit_application_fact') }}

{% endsnapshot %}
