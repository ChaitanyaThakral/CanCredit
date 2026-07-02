"""
Great Expectations — single-entry-point DQ runner for CI.

Consolidates setup_datasource, build_expectations, setup_checkpoint,
and run_checkpoint into one script with a SHARED context so the
ephemeral EphemeralDataContext state is not lost between steps.

Usage:
    python great_expectations/run_dq.py
"""

import os
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

# ── 1. Register Snowflake datasource ──────────────────────────────────────
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

# Register the mart table as a data asset
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

all_columns = [
    "applicant_id", "default_flag", "loan_type", "loan_amount",
    "annual_income", "credit_to_income_ratio", "age_years",
    "credit_risk_segment", "composite_risk_score", "bureau_active_credits",
    "bureau_total_debt", "bureau_total_overdue", "bureau_delinquency_rate",
    "bureau_worst_delinquency", "inst_late_rate", "inst_max_days_late",
    "inst_avg_payment_ratio", "inst_total_underpaid", "cc_avg_utilization",
    "cc_max_utilization", "cc_months_overdue", "prev_num_applications",
    "prev_refusal_rate", "prev_approved", "dbt_updated_at",
]

# Not-null checks
for col in all_columns:
    validator.expect_column_values_to_not_be_null(col)

# Type checks
numeric_cols = [c for c in all_columns if c not in ["loan_type", "credit_risk_segment", "dbt_updated_at"]]
for col in numeric_cols:
    validator.expect_column_values_to_be_in_type_list(col, type_list=["NUMBER", "FLOAT", "INTEGER"])

for col in ["loan_type", "credit_risk_segment"]:
    validator.expect_column_values_to_be_in_type_list(col, type_list=["VARCHAR", "TEXT", "STRING"])

# Numeric range checks
for col in [
    "loan_amount", "annual_income", "bureau_active_credits", "bureau_total_debt",
    "bureau_total_overdue", "inst_max_days_late", "inst_avg_payment_ratio",
    "inst_total_underpaid", "cc_max_utilization", "cc_months_overdue",
    "prev_num_applications", "prev_approved",
]:
    validator.expect_column_values_to_be_between(col, min_value=0, max_value=None)

for col in ["bureau_delinquency_rate", "inst_late_rate", "composite_risk_score", "prev_refusal_rate"]:
    validator.expect_column_values_to_be_between(col, min_value=0, max_value=1)

validator.expect_column_values_to_be_between("credit_to_income_ratio", min_value=0, max_value=100)
validator.expect_column_values_to_be_between("age_years", min_value=18, max_value=120)
validator.expect_column_values_to_be_between("bureau_worst_delinquency", min_value=0, max_value=5)

# Categorical checks
validator.expect_column_values_to_be_in_set("default_flag", [0, 1])
validator.expect_column_values_to_be_in_set("credit_risk_segment", ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"])
validator.expect_column_values_to_be_in_set("loan_type", ["Cash loans", "Revolving loans"])
validator.expect_column_unique_value_count_to_be_between("credit_risk_segment", min_value=4, max_value=4)

# Row count
validator.expect_table_row_count_to_be_between(min_value=250_000, max_value=400_000)

# Cross-column
validator.expect_column_pair_values_a_to_be_greater_than_b(
    column_A="annual_income", column_B="default_flag", or_equal=True
)

# Uniqueness + string lengths + distribution
validator.expect_column_values_to_be_unique("applicant_id")
validator.expect_column_value_lengths_to_be_between("credit_risk_segment", min_value=3, max_value=10)
validator.expect_column_value_lengths_to_be_between("loan_type", min_value=5, max_value=20)
validator.expect_column_mean_to_be_between("default_flag", min_value=0.01, max_value=0.15)
validator.expect_column_median_to_be_between("age_years", min_value=25, max_value=60)

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

# ── 4. Run checkpoint ──────────────────────────────────────────────────────
result = ctx.run_checkpoint(CHECKPOINT_NAME)
assert result.success, "❌ Data quality check failed — see results above."
print("✅ All data quality checks passed.")
