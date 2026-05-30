"""
Plugin: MartRowCountSensor
Purpose: Pokes a Snowflake table and returns True when row count >= min_rows.
Used to guard dbt_marts against partial intermediate builds — if intermediate
tables haven't populated yet the mart run is deferred rather than failing.
"""

from airflow.sensors.base import BaseSensorOperator
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook


class MartRowCountSensor(BaseSensorOperator):
    """
    Sensor that waits until a Snowflake table contains at least `min_rows` rows.

    Args:
        table:    Fully-qualified Snowflake table (DB.SCHEMA.TABLE).
        min_rows: Minimum row count threshold to return True.
        conn_id:  Airflow Snowflake connection ID (default: snowflake_cancredit).
    """

    template_fields = ("table", "min_rows")

    def __init__(
        self,
        table: str,
        min_rows: int,
        conn_id: str = "snowflake_cancredit",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.table = table
        self.min_rows = min_rows
        self.conn_id = conn_id

    def poke(self, context) -> bool:
        hook = SnowflakeHook(snowflake_conn_id=self.conn_id)
        result = hook.get_first(f"SELECT COUNT(*) FROM {self.table}")
        count = result[0] if result else 0
        self.log.info(
            "MartRowCountSensor | %s: %s rows (threshold: %s)",
            self.table,
            f"{count:,}",
            f"{self.min_rows:,}",
        )
        return count >= self.min_rows
