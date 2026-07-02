"""
Great Expectations — single-entry-point DQ runner for CI.

Consolidates setup_datasource, build_expectations, setup_checkpoint,
and run_checkpoint into one script with a SHARED context so the
ephemeral EphemeralDataContext state is not lost between steps.

Expectations are aligned with the actual dbt mart schema
(dbt/cancredit/models/marts/schema.yml) and the SQL model
(mart_credit_application_fact.sql).

Usage:
    python great_expectations/run_dq.py
"""

import os
import sys
import great_expectations as gx

ACCOUNT = os.environ["SNOWFLAKE_ACCOUNT"]
USER = os.environ["SNOWFLAKE_USER"]
PASSWORD = os.environ["SNOWFLAKE_PASSWORD"]

DATASOURCE_NAME = "cancredit_snowflake"
ASSET_NAME = "mart_credit_application_fact"
SUITE_NAME = "mart_fact_suite"
CHECKPOINT_NAME = "cancredit_daily"

# ── Single shared context ──────────────────────────────────────────────────
ctx = gx.get_context()

# ── 1. Register Snowflake datasource + table asset ────────────────────────
datasource = ctx.sources.add_snowflake(
    name=DATASOURCE_NAME,
    account=ACCOUNT,
    user=USER,
    password=PASSWORD,
    database="CANCREDIT_DB",
    schema="MARTS",
    warehouse="CANCREDIT_WH",
    role="SYSADMIN",
)

table_asset = datasource.add_table_asset(
    name=ASSET_NAME,
    table_name="MART_CREDIT_APPLICATION_FACT",
)
batch_request = table_asset.build_batch_request()
print(f"✅ Datasource '{DATASOURCE_NAME}' + asset '{ASSET_NAME}' registered.")

# ── 2. Build expectation suite ────────────────────────────────────────────
suite = ctx.add_or_update_expectation_suite(expectation_suite_name=SUITE_NAME)

validator = ctx.get_validator(
    batch_request=batch_request,
    expectation_suite_name=SUITE_NAME,
)

# ---------------------------------------------------------------------------
# Key columns that dbt guarantees NOT NULL via COALESCE or source tests
# (aligned with schema.yml not_null tests)
# ---------------------------------------------------------------------------
guaranteed_not_null = [
    "applicant_id", "default_flag", "loan_type", "loan_amount",
    "annual_income", "credit_to_income_ratio", "age_years",
    "credit_risk_segment", "composite_risk_score",
    # Bureau (COALESCE to 0 in SQL)
    "bureau_active_credits", "bureau_total_debt", "bureau_total_overdue",
    "bureau_delinquency_rate", "bureau_worst_delinquency",
    # Installment (COALESCE in SQL)
    "inst_late_rate", "inst_max_days_late", "inst_avg_payment_ratio",
    "inst_total_underpaid",
    # Credit card (COALESCE in SQL)
    "cc_avg_utilization", "cc_max_utilization", "cc_months_overdue",
    # Previous apps (COALESCE in SQL)
    "prev_num_applications", "prev_refusal_rate", "prev_approved",
    # Timestamp
    "dbt_updated_at",
]

for col in guaranteed_not_null:
    validator.expect_column_values_to_not_be_null(col)

# ---------------------------------------------------------------------------
# Numeric range checks — aligned with dbt schema.yml and actual SQL logic
# ---------------------------------------------------------------------------

# Non-negative columns (>= 0, as per dbt expression_is_true tests)
non_negative_cols = [
    "loan_amount", "annual_income",
    "bureau_active_credits", "bureau_total_overdue",
    "inst_max_days_late", "inst_avg_payment_ratio", "inst_total_underpaid",
    "cc_max_utilization", "cc_months_overdue",
    "prev_num_applications", "prev_approved",
]
for col in non_negative_cols:
    validator.expect_column_values_to_be_between(col, min_value=0, max_value=None)

# bureau_total_debt can have negative values (credit adjustments) — allow 5% outliers
validator.expect_column_values_to_be_between("bureau_total_debt", min_value=0, max_value=None, mostly=0.95)

# Rate/ratio columns between 0 and 1 (as per schema.yml is_between tests)
rate_cols_0_1 = [
    "bureau_delinquency_rate", "inst_late_rate",
    "composite_risk_score", "prev_refusal_rate",
]
for col in rate_cols_0_1:
    validator.expect_column_values_to_be_between(col, min_value=0, max_value=1)

# credit_to_income_ratio — derived as loan_amount / annual_income
# Per the CASE statement: values can range from 0 to well above 5
# NOT a percentage (0-100), it's a raw ratio
validator.expect_column_values_to_be_between(
    "credit_to_income_ratio", min_value=0, max_value=None
)

# age_years >= 18 (per schema.yml)
validator.expect_column_values_to_be_between("age_years", min_value=18, max_value=None)

# bureau_worst_delinquency: 0-5 (per schema.yml)
validator.expect_column_values_to_be_between("bureau_worst_delinquency", min_value=0, max_value=5)

# cc_avg_utilization: 0-3 (per schema.yml, severity: warn) — allow 5% outliers
validator.expect_column_values_to_be_between("cc_avg_utilization", min_value=0, max_value=3, mostly=0.95)

# ---------------------------------------------------------------------------
# Categorical domain checks
# ---------------------------------------------------------------------------
validator.expect_column_values_to_be_in_set("default_flag", [0, 1])
validator.expect_column_values_to_be_in_set(
    "credit_risk_segment", ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"]
)
validator.expect_column_values_to_be_in_set("loan_type", ["Cash loans", "Revolving loans"])

# ---------------------------------------------------------------------------
# Row count sanity — APPLICATION_TRAIN has 307,511 rows
# Allow a wide margin for filtering or future data changes
# ---------------------------------------------------------------------------
validator.expect_table_row_count_to_be_between(min_value=100_000, max_value=500_000)

# ---------------------------------------------------------------------------
# Uniqueness — applicant_id is the primary key
# ---------------------------------------------------------------------------
validator.expect_column_values_to_be_unique("applicant_id")

# ---------------------------------------------------------------------------
# String length sanity checks
# ---------------------------------------------------------------------------
validator.expect_column_value_lengths_to_be_between(
    "credit_risk_segment", min_value=2, max_value=10
)
validator.expect_column_value_lengths_to_be_between(
    "loan_type", min_value=4, max_value=20
)

# ---------------------------------------------------------------------------
# Distribution sanity (generous bounds)
# ---------------------------------------------------------------------------
# Default rate in Home Credit is ~8%, allow 1-20%
validator.expect_column_mean_to_be_between("default_flag", min_value=0.01, max_value=0.20)

# Median age typically 30-50 for credit applicants
validator.expect_column_median_to_be_between("age_years", min_value=20, max_value=65)

validator.save_expectation_suite(discard_failed_expectations=False)
print(f"✅ Expectation suite '{SUITE_NAME}' saved.")

# ── 3. Register checkpoint ─────────────────────────────────────────────────
ctx.add_or_update_checkpoint(
    name=CHECKPOINT_NAME,
    validations=[
        {
            "batch_request": {
                "datasource_name": DATASOURCE_NAME,
                "data_asset_name": ASSET_NAME,
            },
            "expectation_suite_name": SUITE_NAME,
        }
    ],
    action_list=[
        {"name": "store_validation_result", "action": {"class_name": "StoreValidationResultAction"}},
        {"name": "update_data_docs", "action": {"class_name": "UpdateDataDocsAction"}},
    ],
)
print(f"✅ Checkpoint '{CHECKPOINT_NAME}' registered.")

# ── 4. Run checkpoint and report results ──────────────────────────────────
result = ctx.run_checkpoint(CHECKPOINT_NAME)

# Print detailed results for any failed expectations
for validation_result in result.list_validation_results():
    results_list = validation_result.get("results", [])
    total = len(results_list)
    passed = sum(1 for r in results_list if r["success"])
    failed = total - passed

    print(f"\n📊 Results: {passed}/{total} passed, {failed} failed")

    if failed > 0:
        print("\n❌ Failed expectations:")
        for r in results_list:
            if not r["success"]:
                exp = r.get("expectation_config", {})
                exp_type = exp.get("expectation_type", "unknown")
                kwargs = exp.get("kwargs", {})
                col = kwargs.get("column", kwargs.get("column_A", "table-level"))
                observed = r.get("result", {}).get("observed_value", "N/A")
                print(f"   • {exp_type} on '{col}' — observed: {observed}")

if result.success:
    print("\n✅ All data quality checks passed.")
else:
    print("\n❌ Some data quality checks failed — see details above.")
    sys.exit(1)
