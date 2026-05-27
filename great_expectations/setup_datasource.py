"""
Great Expectations — Snowflake datasource setup script.
Run once to register the Snowflake datasource in your GE context.

Usage:
    python great_expectations/setup_datasource.py
"""
import os
import great_expectations as gx

ACCOUNT  = os.environ['SNOWFLAKE_ACCOUNT']
USER     = os.environ['SNOWFLAKE_USER']
PASSWORD = os.environ['SNOWFLAKE_PASSWORD']


def setup_datasource():
    ctx = gx.get_context()

    ctx.sources.add_snowflake(
        name='cancredit_snowflake',
        account=ACCOUNT,
        user=USER,
        password=PASSWORD,
        database='CANCREDIT_DB',
        schema='MARTS',
        warehouse='CANCREDIT_WH',
        role='SYSADMIN',
    )
    print("✅ Snowflake datasource 'cancredit_snowflake' registered.")
    return ctx


if __name__ == '__main__':
    setup_datasource()
