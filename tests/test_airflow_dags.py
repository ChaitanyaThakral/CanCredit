"""
Unit tests for Airflow DAG logic and the MartRowCountSensor plugin.
Tests operate WITHOUT a live Airflow installation by:
  - Testing boc_logic.py (pure Python, no Airflow imports) directly.
  - Stubbing the entire airflow namespace before importing the sensor plugin.
"""

import sys
import os
import types
import pytest
from unittest.mock import MagicMock, patch

# ── Path setup ──────────────────────────────────────────────────────────────
REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
DAGS_DIR = os.path.join(REPO_ROOT, "airflow", "dags")
PLUGINS_DIR = os.path.join(REPO_ROOT, "airflow", "plugins")

sys.path.insert(0, DAGS_DIR)
sys.path.insert(0, PLUGINS_DIR)


# ===========================================================================
# boc_logic — pure Python, no Airflow dependency
# ===========================================================================
class TestBocLogicFetchLatestBoc:
    """Tests for boc_logic.fetch_latest_boc."""

    @patch("boc_logic.pd.DataFrame.to_csv")
    @patch("boc_logic.requests.get")
    def test_returns_row_count(self, mock_get, mock_to_csv):
        obs = [
            {"d": "2024-01-01", "CAOVERAGE": {"v": "5.00"}},
            {"d": "2024-01-02", "CAOVERAGE": {"v": "4.75"}},
        ]
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"observations": obs}
        mock_get.return_value = mock_resp

        from boc_logic import fetch_latest_boc

        result = fetch_latest_boc("2024-01-01")
        assert result == 2

    @patch("boc_logic.pd.DataFrame.to_csv")
    @patch("boc_logic.requests.get")
    def test_empty_response_returns_zero(self, mock_get, mock_to_csv):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"observations": []}
        mock_get.return_value = mock_resp

        from boc_logic import fetch_latest_boc

        result = fetch_latest_boc("2024-01-01")
        assert result == 0

    @patch("boc_logic.pd.DataFrame.to_csv")
    @patch("boc_logic.requests.get")
    def test_missing_observations_key_returns_zero(self, mock_get, mock_to_csv):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        mock_get.return_value = mock_resp

        from boc_logic import fetch_latest_boc

        result = fetch_latest_boc("2024-01-01")
        assert result == 0

    @patch("boc_logic.pd.DataFrame.to_csv")
    @patch("boc_logic.requests.get")
    def test_csv_written_to_default_path(self, mock_get, mock_to_csv):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"observations": []}
        mock_get.return_value = mock_resp

        from boc_logic import fetch_latest_boc

        fetch_latest_boc("2024-01-01")
        mock_to_csv.assert_called_once_with("/tmp/boc_latest.csv", index=False)

    @patch("boc_logic.pd.DataFrame.to_csv")
    @patch("boc_logic.requests.get")
    def test_csv_written_to_custom_path(self, mock_get, mock_to_csv):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"observations": []}
        mock_get.return_value = mock_resp

        from boc_logic import fetch_latest_boc

        fetch_latest_boc("2024-01-01", output_path="/custom/path.csv")
        mock_to_csv.assert_called_once_with("/custom/path.csv", index=False)

    @patch("boc_logic.pd.DataFrame.to_csv")
    @patch("boc_logic.requests.get")
    def test_api_called_with_start_date(self, mock_get, mock_to_csv):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"observations": []}
        mock_get.return_value = mock_resp

        from boc_logic import fetch_latest_boc

        fetch_latest_boc("2024-03-15")
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["start_date"] == "2024-03-15"

    @patch("boc_logic.pd.DataFrame.to_csv")
    @patch("boc_logic.requests.get")
    def test_api_timeout_is_30_seconds(self, mock_get, mock_to_csv):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"observations": []}
        mock_get.return_value = mock_resp

        from boc_logic import fetch_latest_boc

        fetch_latest_boc("2024-01-01")
        _, kwargs = mock_get.call_args
        assert kwargs["timeout"] == 30

    @patch("boc_logic.pd.DataFrame.to_csv")
    @patch("boc_logic.requests.get")
    def test_non_dict_observation_fields_excluded(self, mock_get, mock_to_csv):
        """The date field 'd' should not appear as a data column."""
        import pandas as pd

        captured_dfs = []
        original_df_init = pd.DataFrame.__init__

        obs = [{"d": "2024-01-01", "CAOVERAGE": {"v": "5.0"}}]
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"observations": obs}
        mock_get.return_value = mock_resp

        from boc_logic import fetch_latest_boc

        with patch("boc_logic.pd.DataFrame") as mock_df_cls:
            mock_df_instance = MagicMock()
            mock_df_cls.return_value = mock_df_instance
            fetch_latest_boc("2024-01-01")
            rows_arg = mock_df_cls.call_args[0][0]
            assert len(rows_arg) == 1
            assert "d" not in rows_arg[0]
            assert rows_arg[0]["obs_date"] == "2024-01-01"


# ===========================================================================
# boc_logic — branch_on_rows
# ===========================================================================
class TestBocLogicBranchOnRows:
    """Tests for boc_logic.branch_on_rows."""

    def setup_method(self):
        from boc_logic import branch_on_rows

        self.fn = branch_on_rows

    def test_positive_count_returns_load(self):
        assert self.fn(5) == "load_boc"

    def test_zero_count_returns_skip(self):
        assert self.fn(0) == "skip_boc"

    def test_none_returns_skip(self):
        assert self.fn(None) == "skip_boc"

    def test_one_returns_load(self):
        assert self.fn(1) == "load_boc"

    def test_large_count_returns_load(self):
        assert self.fn(1_000_000) == "load_boc"


# ===========================================================================
# MartRowCountSensor — stub Airflow namespace before import
# ===========================================================================
def _stub_airflow():
    """Register mock airflow.sensors.base so the sensor can be imported."""
    if "airflow" not in sys.modules or not hasattr(sys.modules["airflow"], "sensors"):
        airflow_mod = types.ModuleType("airflow")
        sensors_mod = types.ModuleType("airflow.sensors")
        base_mod = types.ModuleType("airflow.sensors.base")
        providers_mod = types.ModuleType("airflow.providers")
        sf_mod = types.ModuleType("airflow.providers.snowflake")
        hooks_mod = types.ModuleType("airflow.providers.snowflake.hooks")
        hook_mod = types.ModuleType("airflow.providers.snowflake.hooks.snowflake")

        # BaseSensorOperator: minimal stub
        class BaseSensorOperator:
            template_fields = ()

            def __init__(self, task_id, poke_interval=60, timeout=60 * 60, **kwargs):
                self.task_id = task_id
                self.poke_interval = poke_interval
                self.timeout = timeout
                self.log = MagicMock()

            def poke(self, context):
                raise NotImplementedError

        base_mod.BaseSensorOperator = BaseSensorOperator
        hook_mod.SnowflakeHook = MagicMock

        sys.modules["airflow"] = airflow_mod
        sys.modules["airflow.sensors"] = sensors_mod
        sys.modules["airflow.sensors.base"] = base_mod
        sys.modules["airflow.providers"] = providers_mod
        sys.modules["airflow.providers.snowflake"] = sf_mod
        sys.modules["airflow.providers.snowflake.hooks"] = hooks_mod
        sys.modules["airflow.providers.snowflake.hooks.snowflake"] = hook_mod


_stub_airflow()


class TestMartRowCountSensor:
    """Tests for the MartRowCountSensor plugin."""

    def _make_sensor(
        self, table="DB.SCHEMA.TABLE", min_rows=1000, conn_id="snowflake_cancredit"
    ):
        from snowflake_mart_sensor import MartRowCountSensor

        return MartRowCountSensor(
            task_id="test_sensor", table=table, min_rows=min_rows, conn_id=conn_id
        )

    @patch("snowflake_mart_sensor.SnowflakeHook")
    def test_poke_true_when_count_meets_threshold(self, mock_hook_cls):
        mock_hook_cls.return_value.get_first.return_value = (1_500_000,)
        assert self._make_sensor(min_rows=1_000_000).poke({}) is True

    @patch("snowflake_mart_sensor.SnowflakeHook")
    def test_poke_false_when_count_below_threshold(self, mock_hook_cls):
        mock_hook_cls.return_value.get_first.return_value = (500,)
        assert self._make_sensor(min_rows=1_000_000).poke({}) is False

    @patch("snowflake_mart_sensor.SnowflakeHook")
    def test_poke_true_at_exact_threshold(self, mock_hook_cls):
        mock_hook_cls.return_value.get_first.return_value = (100,)
        assert self._make_sensor(min_rows=100).poke({}) is True

    @patch("snowflake_mart_sensor.SnowflakeHook")
    def test_poke_false_when_result_is_none(self, mock_hook_cls):
        mock_hook_cls.return_value.get_first.return_value = None
        assert self._make_sensor(min_rows=1).poke({}) is False

    @patch("snowflake_mart_sensor.SnowflakeHook")
    def test_uses_correct_conn_id(self, mock_hook_cls):
        mock_hook_cls.return_value.get_first.return_value = (100,)
        self._make_sensor(conn_id="my_custom_conn").poke({})
        mock_hook_cls.assert_called_once_with(snowflake_conn_id="my_custom_conn")

    @patch("snowflake_mart_sensor.SnowflakeHook")
    def test_queries_correct_table(self, mock_hook_cls):
        mock_hook_cls.return_value.get_first.return_value = (99,)
        self._make_sensor(table="CANCREDIT_DB.INT.INT_BUREAU_FEATURES").poke({})
        sql = mock_hook_cls.return_value.get_first.call_args[0][0]
        assert "CANCREDIT_DB.INT.INT_BUREAU_FEATURES" in sql

    def test_sensor_stores_table_and_min_rows(self):
        sensor = self._make_sensor(table="MY.TABLE", min_rows=42)
        assert sensor.table == "MY.TABLE"
        assert sensor.min_rows == 42

    def test_default_conn_id(self):
        sensor = self._make_sensor()
        assert sensor.conn_id == "snowflake_cancredit"
