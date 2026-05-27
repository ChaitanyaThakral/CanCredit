"""
Great Expectations — Expectation Suite builder for mart_credit_application_fact.
Creates and saves a suite of 12 expectations covering:
  - Completeness (not-null key columns)
  - Domain validity (accepted values, numeric ranges)
  - Row count bounds
  - Cross-column relationships (annuity <= loan amount)

Usage:
    python great_expectations/build_expectations.py
"""
import os
import great_expectations as gx


def build_mart_fact_suite():
    ctx = gx.get_context()

    # ── Create suite ──────────────────────────────────────────────────────
    suite_name = 'mart_fact_suite'
    suite = ctx.add_or_update_expectation_suite(expectation_suite_name=suite_name)

    # Get validator bound to the mart fact table
    validator = ctx.get_validator(
        datasource_name='cancredit_snowflake',
        data_asset_name='mart_credit_application_fact',
        expectation_suite_name=suite_name,
    )

    # ── 1–4: Completeness ─────────────────────────────────────────────────
    validator.expect_column_values_to_not_be_null('applicant_id')
    validator.expect_column_values_to_not_be_null('default_flag')
    validator.expect_column_values_to_not_be_null('loan_amount')
    validator.expect_column_values_to_not_be_null('credit_risk_segment')

    # ── 5–6: Categorical domain validity ─────────────────────────────────
    validator.expect_column_values_to_be_in_set('default_flag', [0, 1])
    validator.expect_column_values_to_be_in_set(
        'credit_risk_segment', ['LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH']
    )

    # ── 7–10: Numeric range validity ─────────────────────────────────────
    validator.expect_column_values_to_be_between(
        'credit_to_income_ratio', min_value=0, max_value=100
    )
    validator.expect_column_values_to_be_between(
        'bureau_delinquency_rate', min_value=0, max_value=1
    )
    validator.expect_column_values_to_be_between(
        'inst_late_rate', min_value=0, max_value=1
    )
    validator.expect_column_values_to_be_between(
        'composite_risk_score', min_value=0, max_value=1
    )

    # ── 11: Row count sanity check ────────────────────────────────────────
    # APPLICATION_TRAIN has 307,511 rows → mart should be within this range
    validator.expect_table_row_count_to_be_between(
        min_value=250_000, max_value=400_000
    )

    # ── 12: Cross-column relationship ─────────────────────────────────────
    # Loan annuity (monthly repayment) should never exceed total loan amount
    validator.expect_column_pair_values_a_to_be_greater_than_or_equal_to_b(
        column_A='loan_amount',
        column_B='loan_annuity',
    )

    validator.save_expectation_suite(discard_failed_expectations=False)
    print(f"✅ Expectation suite '{suite_name}' saved with 12 expectations.")
    return validator


if __name__ == '__main__':
    build_mart_fact_suite()
