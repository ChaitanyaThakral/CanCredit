"""
Great Expectations — Expectation Suite builder for mart_credit_application_fact.
Creates and saves a suite of expectations covering:
  - Completeness (not-null key columns)
  - Domain validity (accepted values, numeric ranges)
  - Row count bounds
  - Uniqueness and string length checks
  - Distribution sanity (mean / median)

Expectations are aligned with the dbt schema.yml and actual SQL model.

Usage:
    python great_expectations/build_expectations.py
"""

import great_expectations as gx


def build_mart_fact_suite(ctx=None):
    if ctx is None:
        ctx = gx.get_context()

    suite_name = "mart_fact_suite"
    datasource_name = "cancredit_snowflake"
    asset_name = "mart_credit_application_fact"

    # ── Create suite ──────────────────────────────────────────────────────
    suite = ctx.add_or_update_expectation_suite(expectation_suite_name=suite_name)

    # Get validator via batch_request from the registered table asset
    datasource = ctx.get_datasource(datasource_name)
    table_asset = datasource.get_asset(asset_name)
    batch_request = table_asset.build_batch_request()

    validator = ctx.get_validator(
        batch_request=batch_request,
        expectation_suite_name=suite_name,
    )

    # ── Not-null checks (columns guaranteed by COALESCE or source tests) ──
    guaranteed_not_null = [
        "applicant_id", "default_flag", "loan_type", "loan_amount",
        "annual_income", "credit_to_income_ratio", "age_years",
        "credit_risk_segment", "composite_risk_score",
        "bureau_active_credits", "bureau_total_debt", "bureau_total_overdue",
        "bureau_delinquency_rate", "bureau_worst_delinquency",
        "inst_late_rate", "inst_max_days_late", "inst_avg_payment_ratio",
        "inst_total_underpaid",
        "cc_avg_utilization", "cc_max_utilization", "cc_months_overdue",
        "prev_num_applications", "prev_refusal_rate", "prev_approved",
        "dbt_updated_at",
    ]
    for col in guaranteed_not_null:
        validator.expect_column_values_to_not_be_null(col)

    # ── Non-negative columns ──────────────────────────────────────────────
    non_negative_cols = [
        "loan_amount", "annual_income",
        "bureau_active_credits", "bureau_total_debt", "bureau_total_overdue",
        "inst_max_days_late", "inst_avg_payment_ratio", "inst_total_underpaid",
        "cc_max_utilization", "cc_months_overdue",
        "prev_num_applications", "prev_approved",
    ]
    for col in non_negative_cols:
        validator.expect_column_values_to_be_between(col, min_value=0, max_value=None)

    # ── Rate/ratio columns 0-1 ────────────────────────────────────────────
    for col in ["bureau_delinquency_rate", "inst_late_rate", "composite_risk_score", "prev_refusal_rate"]:
        validator.expect_column_values_to_be_between(col, min_value=0, max_value=1)

    # ── Specific range checks ─────────────────────────────────────────────
    validator.expect_column_values_to_be_between("credit_to_income_ratio", min_value=0, max_value=None)
    validator.expect_column_values_to_be_between("age_years", min_value=18, max_value=None)
    validator.expect_column_values_to_be_between("bureau_worst_delinquency", min_value=0, max_value=5)
    validator.expect_column_values_to_be_between("cc_avg_utilization", min_value=0, max_value=3)

    # ── Categorical domain checks ─────────────────────────────────────────
    validator.expect_column_values_to_be_in_set("default_flag", [0, 1])
    validator.expect_column_values_to_be_in_set("credit_risk_segment", ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"])
    validator.expect_column_values_to_be_in_set("loan_type", ["Cash loans", "Revolving loans"])

    # ── Row count ─────────────────────────────────────────────────────────
    validator.expect_table_row_count_to_be_between(min_value=100_000, max_value=500_000)

    # ── Uniqueness ────────────────────────────────────────────────────────
    validator.expect_column_values_to_be_unique("applicant_id")

    # ── String length checks ──────────────────────────────────────────────
    validator.expect_column_value_lengths_to_be_between("credit_risk_segment", min_value=2, max_value=10)
    validator.expect_column_value_lengths_to_be_between("loan_type", min_value=4, max_value=20)

    # ── Distribution sanity ───────────────────────────────────────────────
    validator.expect_column_mean_to_be_between("default_flag", min_value=0.01, max_value=0.20)
    validator.expect_column_median_to_be_between("age_years", min_value=20, max_value=65)

    validator.save_expectation_suite(discard_failed_expectations=False)
    print(f"✅ Expectation suite '{suite_name}' saved.")
    return validator


if __name__ == "__main__":
    build_mart_fact_suite()
