-- macros/test_is_between.sql
-- Generic dbt test: is_between
--
-- Usage in schema.yml (nested arguments style, matches existing schema.yml):
--   columns:
--     - name: composite_risk_score
--       tests:
--         - is_between:
--             arguments:
--               min_value: 0
--               max_value: 1
--
-- Returns rows that FAIL the test (value outside [min_value, max_value]).
-- dbt counts failures — 0 rows = PASS, any rows = FAIL.

{% test is_between(model, column_name, arguments) %}

SELECT {{ column_name }}
FROM {{ model }}
WHERE {{ column_name }} IS NOT NULL
  AND (
      {{ column_name }} < {{ arguments['min_value'] }}
      OR {{ column_name }} > {{ arguments['max_value'] }}
  )

{% endtest %}
