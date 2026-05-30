"""
DAG: cancredit_pipeline
Schedule: 07:00 ET, Mon-Fri
Purpose: Master orchestration DAG — validates raw data, runs dbt transformation
         layers in sequence, then executes Great Expectations data quality checkpoint.

Pipeline topology:
    validate_raw_row_count
        → dbt_staging  (8 staging views)
        → mart_sensor  (guards against partial intermediate builds)
        → dbt_intermediate  (4 intermediate tables)
        → dbt_marts  (3 mart + 1 ML feature table)
        → run_data_quality  (GE checkpoint)
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator
from cosmos import DbtTaskGroup, ProjectConfig, ProfileConfig, RenderConfig
from cosmos.constants import LoadMode
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, "/opt/airflow/plugins")
from snowflake_mart_sensor import MartRowCountSensor  # noqa: E402

default_args = {
    "owner": "cancredit",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": True,
    "email": ["admin@cancredit.local"],
}

DBT_PROJECT_PATH = Path("/opt/airflow/dbt/cancredit")
DBT_PROFILES_PATH = Path("/opt/airflow/dbt")

PROFILE_CONFIG = ProfileConfig(
    profile_name="cancredit",
    target_name="prod",
    profiles_yml_filepath=DBT_PROFILES_PATH / "profiles.yml",
)

# Validates the raw APPLICATION_TRAIN table has the expected row count.
# Returning NULL causes the SnowflakeOperator to fail the task.
ROW_COUNT_SQL = """
SELECT CASE WHEN COUNT(*) >= 300000 THEN 'PASS'
            ELSE NULL END
FROM CANCREDIT_DB.RAW.APPLICATION_TRAIN;
"""


def run_ge_checkpoint():
    """Execute the Great Expectations daily checkpoint."""
    import great_expectations as gx

    context = gx.get_context()
    result = context.run_checkpoint("cancredit_daily")
    if not result.success:
        raise ValueError(
            f"Great Expectations checkpoint FAILED. "
            f"Results: {result.to_json_dict()}"
        )
    return "GE checkpoint passed."


with DAG(
    "cancredit_pipeline",
    default_args=default_args,
    schedule="0 7 * * 1-5",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["pipeline", "cancredit"],
    description="Master CanCredit transformation pipeline: validate → dbt → GE",
) as dag:

    # ── 1. Raw data validation ─────────────────────────────────────────────
    validate_raw = SnowflakeOperator(
        task_id="validate_raw_row_count",
        snowflake_conn_id="snowflake_cancredit",
        sql=ROW_COUNT_SQL,
    )

    # ── 2. dbt Staging layer ───────────────────────────────────────────────
    dbt_staging = DbtTaskGroup(
        group_id="dbt_staging",
        project_config=ProjectConfig(DBT_PROJECT_PATH),
        profile_config=PROFILE_CONFIG,
        render_config=RenderConfig(
            load_method=LoadMode.DBT_LS,
            select=["staging"],
        ),
    )

    # ── 3. Sensor: guard mart run against partial intermediate builds ───────
    mart_sensor = MartRowCountSensor(
        task_id="wait_for_bureau_features",
        table="CANCREDIT_DB.INTERMEDIATE.INT_BUREAU_FEATURES",
        min_rows=1,
        poke_interval=60,
        timeout=600,
    )

    # ── 4. dbt Intermediate layer ──────────────────────────────────────────
    dbt_intermediate = DbtTaskGroup(
        group_id="dbt_intermediate",
        project_config=ProjectConfig(DBT_PROJECT_PATH),
        profile_config=PROFILE_CONFIG,
        render_config=RenderConfig(
            load_method=LoadMode.DBT_LS,
            select=["intermediate"],
        ),
    )

    # ── 5. dbt Mart + ML feature store layer ──────────────────────────────
    dbt_marts = DbtTaskGroup(
        group_id="dbt_marts",
        project_config=ProjectConfig(DBT_PROJECT_PATH),
        profile_config=PROFILE_CONFIG,
        render_config=RenderConfig(
            load_method=LoadMode.DBT_LS,
            select=["marts"],
        ),
    )

    # ── 6. Great Expectations data quality checkpoint ─────────────────────
    run_ge = PythonOperator(
        task_id="run_data_quality",
        python_callable=run_ge_checkpoint,
    )

    # ── DAG topology ──────────────────────────────────────────────────────
    (
        validate_raw
        >> dbt_staging
        >> mart_sensor
        >> dbt_intermediate
        >> dbt_marts
        >> run_ge
    )
