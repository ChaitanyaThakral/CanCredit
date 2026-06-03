{% macro generate_schema_name(custom_schema_name, node) -%}
    {#-
        Override the default dbt behavior so that when a custom_schema_name
        is provided (either via +schema in dbt_project.yml or {{ config(schema=...) }}),
        it is used AS-IS without being prefixed by the default schema.
        This ensures:
          - staging models  → CANCREDIT_DB.STAGING
          - intermediate    → CANCREDIT_DB.INTERMEDIATE
          - marts           → CANCREDIT_DB.MARTS
          - ml_features_training → CANCREDIT_DB.ML_FEATURES
    -#}
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- else -%}
        {{ custom_schema_name | trim | upper }}
    {%- endif -%}
{%- endmacro %}
