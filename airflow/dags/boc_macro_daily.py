"""
DAG: boc_macro_daily
Schedule: 06:00 ET, Mon-Fri
Purpose: Fetch latest Bank of Canada macro indicators and load into Snowflake RAW layer.
         Branches to skip gracefully when the API returns no new observations.
"""
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator
from datetime import datetime, timedelta
from boc_logic import fetch_latest_boc as _fetch, branch_on_rows as _branch

default_args = {
    'owner': 'cancredit',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'email_on_failure': True,
    'email': ['admin@cancredit.local'],
}


def fetch_latest_boc_task(**context):
    """Airflow task wrapper — delegates to boc_logic.fetch_latest_boc."""
    last_date = context['data_interval_start'].strftime('%Y-%m-%d')
    count = _fetch(last_date)
    context['ti'].log.info(f"Fetched {count} BOC observations from {last_date}")
    return count


def branch_on_rows_task(**ctx):
    """Airflow task wrapper — delegates to boc_logic.branch_on_rows."""
    rows = ctx['ti'].xcom_pull(task_ids='fetch_boc')
    return _branch(rows)


def skip_handler():
    print("No new BOC data for this interval — skipping load.")


# COPY INTO assumes a pre-staged internal stage; actual file upload
# (PUT) would be handled by a preceding PythonOperator in production.
COPY_SQL = """
COPY INTO CANCREDIT_DB.RAW.BOC_MACRO
FROM @CANCREDIT_DB.RAW.BOC_STAGE/boc_latest.csv
FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1)
ON_ERROR = 'ABORT_STATEMENT';
"""

with DAG(
    'boc_macro_daily',
    default_args=default_args,
    schedule='0 6 * * 1-5',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['ingestion', 'macro'],
    description='Daily BOC macro indicator refresh into Snowflake RAW layer',
) as dag:

    fetch = PythonOperator(
        task_id='fetch_boc',
        python_callable=fetch_latest_boc_task,
    )

    branch = BranchPythonOperator(
        task_id='check_rows',
        python_callable=branch_on_rows_task,
    )

    load = SnowflakeOperator(
        task_id='load_boc',
        snowflake_conn_id='snowflake_cancredit',
        sql=COPY_SQL,
    )

    skip = PythonOperator(
        task_id='skip_boc',
        python_callable=skip_handler,
    )

    fetch >> branch >> [load, skip]
