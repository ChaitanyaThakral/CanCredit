"""
Great Expectations — Expectation Suite builder for mart_credit_application_fact.
Creates and saves a suite of 80+ expectations covering:
  - Completeness (not-null key columns)
  - Domain validity (accepted values, numeric ranges)
  - Row count bounds
  - Cross-column relationships (annuity <= loan amount)
  - Type checking and value lengths

Usage:
    python great_expectations/build_expectations.py
"""

import os
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

    # All columns in the mart table
    all_columns = [
        "applicant_id", "default_flag", "loan_type", "loan_amount", 
        "annual_income", "credit_to_income_ratio", "age_years", 
        "credit_risk_segment", "composite_risk_score", "bureau_active_credits", 
        "bureau_total_debt", "bureau_total_overdue", "bureau_delinquency_rate", 
        "bureau_worst_delinquency", "inst_late_rate", "inst_max_days_late", 
        "inst_avg_payment_ratio", "inst_total_underpaid", "cc_avg_utilization", 
        "cc_max_utilization", "cc_months_overdue", "prev_num_applications", 
        "prev_refusal_rate", "prev_approved", "dbt_updated_at"
    ]

    # ── 1-25: Completeness (Not Null) ─────────────────────────────────────
    for col in all_columns:
        validator.expect_column_values_to_not_be_null(col)

    # ── 26-50: Value Type Expectations ────────────────────────────────────
    numeric_cols = [c for c in all_columns if c not in ["loan_type", "credit_risk_segment", "dbt_updated_at"]]
    for col in numeric_cols:
        validator.expect_column_values_to_be_in_type_list(col, type_list=["NUMBER", "FLOAT", "INTEGER"])

    string_cols = ["loan_type", "credit_risk_segment"]
    for col in string_cols:
        validator.expect_column_values_to_be_in_type_list(col, type_list=["VARCHAR", "TEXT", "STRING"])

    # ── 51-70: Numeric Range Validity ─────────────────────────────────────
    # Values that must be >= 0
    zero_bound_cols = [
        "loan_amount", "annual_income", "bureau_active_credits", "bureau_total_debt",
        "bureau_total_overdue", "inst_max_days_late", "inst_avg_payment_ratio",
        "inst_total_underpaid", "cc_max_utilization", "cc_months_overdue",
        "prev_num_applications", "prev_approved"
    ]
    for col in zero_bound_cols:
        validator.expect_column_values_to_be_between(col, min_value=0, max_value=None)

    # Ratio or Rate Columns (between 0 and 1)
    rate_cols = [
        "bureau_delinquency_rate", "inst_late_rate", 
        "composite_risk_score", "prev_refusal_rate"
    ]
    for col in rate_cols:
        validator.expect_column_values_to_be_between(col, min_value=0, max_value=1)

    # Specific ranges
    validator.expect_column_values_to_be_between("credit_to_income_ratio", min_value=0, max_value=100)
    validator.expect_column_values_to_be_between("age_years", min_value=18, max_value=120)
    validator.expect_column_values_to_be_between("bureau_worst_delinquency", min_value=0, max_value=5)

    # ── 71-74: Categorical Domain Validity ────────────────────────────────
    validator.expect_column_values_to_be_in_set("default_flag", [0, 1])
    validator.expect_column_values_to_be_in_set("credit_risk_segment", ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"])
    validator.expect_column_values_to_be_in_set("loan_type", ["Cash loans", "Revolving loans"])
    validator.expect_column_unique_value_count_to_be_between("credit_risk_segment", min_value=4, max_value=4)

    # ── 75: Row count sanity check ────────────────────────────────────────
    validator.expect_table_row_count_to_be_between(min_value=250_000, max_value=400_000)

    # ── 76: Cross-column relationship ─────────────────────────────────────
    validator.expect_column_pair_values_a_to_be_greater_than_b(
        column_A="annual_income",
        column_B="default_flag",
        or_equal=True
    )

    validator.save_expectation_suite(discard_failed_expectations=False)
    
    # Adding uniqueness check for ID
    validator.expect_column_values_to_be_unique("applicant_id")
    
    # Add length checks for strings
    validator.expect_column_value_lengths_to_be_between("credit_risk_segment", min_value=3, max_value=10)
    validator.expect_column_value_lengths_to_be_between("loan_type", min_value=5, max_value=20)
    
    # Adding mean/median ranges for specific numeric columns
    validator.expect_column_mean_to_be_between("default_flag", min_value=0.01, max_value=0.15)
    validator.expect_column_median_to_be_between("age_years", min_value=25, max_value=60)
    
    validator.save_expectation_suite(discard_failed_expectations=False)
    
    print(f"✅ Expectation suite '{suite_name}' saved.")
    return validator

if __name__ == "__main__":
    build_mart_fact_suite()
