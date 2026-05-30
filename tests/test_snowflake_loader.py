"""
Unit tests for ingestion/snowflake_loader.py
Coverage: get_snowflake_conn, infer_ddl, load_csv_chunked
"""

import io
import sys
import os
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, call

# Make ingestion importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ingestion"))
import snowflake_loader as sl


# ---------------------------------------------------------------------------
# infer_ddl
# ---------------------------------------------------------------------------
class TestInferDdl:
    def _df(self, dtypes: dict) -> pd.DataFrame:
        """Build a minimal DataFrame with the requested dtypes."""
        data = {col: pd.array([0], dtype=dtype) for col, dtype in dtypes.items()}
        return pd.DataFrame(data)

    def test_int64_column(self):
        df = self._df({"my_int": "int64"})
        ddl = sl.infer_ddl(df, "MY_TABLE")
        assert '"MY_INT" NUMBER' in ddl
        assert ddl.startswith("CREATE TABLE IF NOT EXISTS MY_TABLE")

    def test_float64_column(self):
        df = self._df({"score": "float64"})
        ddl = sl.infer_ddl(df, "T")
        assert '"SCORE" FLOAT' in ddl

    def test_object_column(self):
        df = pd.DataFrame({"name": pd.array(["a"], dtype="object")})
        ddl = sl.infer_ddl(df, "T")
        assert '"NAME" VARCHAR(500)' in ddl

    def test_bool_column(self):
        df = pd.DataFrame({"flag": pd.array([True], dtype="bool")})
        ddl = sl.infer_ddl(df, "T")
        assert '"FLAG" BOOLEAN' in ddl

    def test_datetime_ns_column(self):
        """Legacy pandas datetime dtype — still supported."""
        df = pd.DataFrame({"ts": pd.array(["2024-01-01"], dtype="datetime64[ns]")})
        ddl = sl.infer_ddl(df, "T")
        assert '"TS" TIMESTAMP_NTZ' in ddl

    def test_datetime_us_column(self):
        """Pandas 3.x default datetime dtype."""
        df = pd.DataFrame({"ts": pd.to_datetime(["2024-01-01"])})
        # Confirm this is the modern us-resolution dtype
        assert "datetime64" in str(df.dtypes["ts"])
        ddl = sl.infer_ddl(df, "T")
        assert '"TS" TIMESTAMP_NTZ' in ddl

    def test_unknown_dtype_falls_back_to_varchar(self):
        # category dtype is not in the type_map
        df = pd.DataFrame({"cat": pd.Categorical(["a", "b"])})
        ddl = sl.infer_ddl(df, "T")
        assert '"CAT" VARCHAR(500)' in ddl

    def test_multiple_columns(self):
        df = pd.DataFrame(
            {
                "id": pd.array([1], dtype="int64"),
                "val": pd.array([1.0], dtype="float64"),
                "label": pd.array(["x"], dtype="object"),
            }
        )
        ddl = sl.infer_ddl(df, "MULTI")
        assert '"ID" NUMBER' in ddl
        assert '"VAL" FLOAT' in ddl
        assert '"LABEL" VARCHAR(500)' in ddl

    def test_column_names_are_uppercased(self):
        df = pd.DataFrame({"myCol": pd.array([1], dtype="int64")})
        ddl = sl.infer_ddl(df, "T")
        assert '"MYCOL"' in ddl
        assert "myCol" not in ddl

    def test_table_name_embedded_verbatim(self):
        df = pd.DataFrame({"x": pd.array([1], dtype="int64")})
        ddl = sl.infer_ddl(df, "CANCREDIT_DB.RAW.MY_TABLE")
        assert "CANCREDIT_DB.RAW.MY_TABLE" in ddl


# ---------------------------------------------------------------------------
# get_snowflake_conn
# ---------------------------------------------------------------------------
class TestGetSnowflakeConn:
    @patch("snowflake_loader.snowflake.connector.connect")
    def test_passes_config_fields(self, mock_connect):
        config = {"account": "acc1", "user": "usr1", "password": "pw1"}
        sl.get_snowflake_conn(config)
        mock_connect.assert_called_once_with(
            account="acc1",
            user="usr1",
            password="pw1",
            database="CANCREDIT_DB",
            schema="RAW",
            warehouse="CANCREDIT_WH",
        )

    @patch("snowflake_loader.snowflake.connector.connect")
    def test_returns_connection_object(self, mock_connect):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        config = {"account": "a", "user": "u", "password": "p"}
        result = sl.get_snowflake_conn(config)
        assert result is mock_conn

    @patch("snowflake_loader.snowflake.connector.connect")
    def test_uses_fixed_database_and_warehouse(self, mock_connect):
        config = {"account": "a", "user": "u", "password": "p"}
        sl.get_snowflake_conn(config)
        _, kwargs = mock_connect.call_args
        assert kwargs["database"] == "CANCREDIT_DB"
        assert kwargs["warehouse"] == "CANCREDIT_WH"
        assert kwargs["schema"] == "RAW"


# ---------------------------------------------------------------------------
# load_csv_chunked
# ---------------------------------------------------------------------------
class TestLoadCsvChunked:
    def _make_csv(self, tmp_path, rows=None):
        """Write a tiny CSV and return its path."""
        rows = rows or [{"id": 1, "val": 10.5}, {"id": 2, "val": 20.0}]
        df = pd.DataFrame(rows)
        p = tmp_path / "test.csv"
        df.to_csv(p, index=False)
        return str(p)

    @patch("snowflake_loader.write_pandas")
    @patch("snowflake_loader.get_snowflake_conn")
    def test_single_chunk_creates_table_once(self, mock_conn_fn, mock_wp, tmp_path):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn_fn.return_value = mock_conn

        csv_path = self._make_csv(tmp_path)
        sl.load_csv_chunked(csv_path, "MY_TABLE", {}, chunksize=1000)

        # DROP + CREATE for chunk 0
        assert mock_cursor.execute.call_count == 2
        drop_call = mock_cursor.execute.call_args_list[0][0][0]
        assert "DROP TABLE IF EXISTS" in drop_call
        assert "MY_TABLE" in drop_call

    @patch("snowflake_loader.write_pandas")
    @patch("snowflake_loader.get_snowflake_conn")
    def test_write_pandas_called_per_chunk(self, mock_conn_fn, mock_wp, tmp_path):
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = MagicMock()
        mock_conn_fn.return_value = mock_conn

        # 4 rows, chunksize=2 → 2 calls to write_pandas
        rows = [{"id": i, "v": i * 1.0} for i in range(4)]
        csv_path = self._make_csv(tmp_path, rows)
        sl.load_csv_chunked(csv_path, "T", {}, chunksize=2)
        assert mock_wp.call_count == 2

    @patch("snowflake_loader.write_pandas")
    @patch("snowflake_loader.get_snowflake_conn")
    def test_loaded_at_column_added(self, mock_conn_fn, mock_wp, tmp_path):
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = MagicMock()
        mock_conn_fn.return_value = mock_conn

        csv_path = self._make_csv(tmp_path)
        sl.load_csv_chunked(csv_path, "T", {}, chunksize=1000)

        # First positional arg to write_pandas is the chunk DataFrame
        chunk_df = mock_wp.call_args_list[0][0][1]
        assert "LOADED_AT" in chunk_df.columns

    @patch("snowflake_loader.write_pandas")
    @patch("snowflake_loader.get_snowflake_conn")
    def test_connection_closed_after_load(self, mock_conn_fn, mock_wp, tmp_path):
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = MagicMock()
        mock_conn_fn.return_value = mock_conn

        csv_path = self._make_csv(tmp_path)
        sl.load_csv_chunked(csv_path, "T", {}, chunksize=1000)
        mock_conn.close.assert_called_once()

    @patch("snowflake_loader.write_pandas")
    @patch("snowflake_loader.get_snowflake_conn")
    def test_write_pandas_uses_correct_database_and_schema(
        self, mock_conn_fn, mock_wp, tmp_path
    ):
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = MagicMock()
        mock_conn_fn.return_value = mock_conn

        csv_path = self._make_csv(tmp_path)
        sl.load_csv_chunked(csv_path, "MYTABLE", {}, chunksize=1000)

        _, wp_kwargs = mock_wp.call_args
        assert wp_kwargs["database"] == "CANCREDIT_DB"
        assert wp_kwargs["schema"] == "RAW"
        assert wp_kwargs["overwrite"] is False

    @patch("snowflake_loader.write_pandas")
    @patch("snowflake_loader.get_snowflake_conn")
    def test_no_ddl_execute_after_first_chunk(self, mock_conn_fn, mock_wp, tmp_path):
        """For chunk index > 0, cursor.execute should NOT be called again."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn_fn.return_value = mock_conn

        # 4 rows, chunksize=2 → 2 chunks; execute only runs for i==0
        rows = [{"id": i} for i in range(4)]
        csv_path = self._make_csv(tmp_path, rows)
        sl.load_csv_chunked(csv_path, "T", {}, chunksize=2)
        # Only 2 execute calls total (DROP + CREATE on first chunk only)
        assert mock_cursor.execute.call_count == 2
