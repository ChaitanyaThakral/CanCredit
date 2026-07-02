"""
Great Expectations — Snowflake datasource setup script.
Run once to register the Snowflake datasource in your GE context.

Usage:
    python great_expectations/setup_datasource.py
"""

import os
import great_expectations as gx

ACCOUNT = os.environ["SNOWFLAKE_ACCOUNT"]
USER = os.environ["SNOWFLAKE_USER"]
PASSWORD = os.environ["SNOWFLAKE_PASSWORD"]


def setup_datasource(ctx=None):
    if ctx is None:
        ctx = gx.get_context()

    # Register the Snowflake datasource
    datasource = ctx.sources.add_snowflake(
        name="cancredit_snowflake",
        account=ACCOUNT,
        user=USER,
        password=PASSWORD,
        database="CANCREDIT_DB",
        schema="MARTS",
        warehouse="CANCREDIT_WH",
        role="SYSADMIN",
    )

    # Explicitly register table asset (required in GX 0.18.x fluent API)
    table_asset = datasource.add_table_asset(
        name="mart_credit_application_fact",
        table_name="MART_CREDIT_APPLICATION_FACT",
    )

    print("✅ Snowflake datasource 'cancredit_snowflake' registered with table asset.")
    return ctx, datasource, table_asset


if __name__ == "__main__":
    setup_datasource()
