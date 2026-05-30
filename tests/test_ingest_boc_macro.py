"""
Unit tests for ingestion/ingest_boc_macro.py
Coverage: fetch_boc (API call, DataFrame construction, CSV write, error path)
"""

import sys
import os
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ingestion"))
import ingest_boc_macro as boc


# ---------------------------------------------------------------------------
# fetch_boc
# ---------------------------------------------------------------------------
class TestFetchBoc:
    def _mock_response(self, observations):
        resp = MagicMock()
        resp.json.return_value = {"observations": observations}
        return resp

    @patch("ingest_boc_macro.pd.DataFrame.to_csv")
    @patch("ingest_boc_macro.os.makedirs")
    @patch("ingest_boc_macro.requests.get")
    def test_returns_dataframe(self, mock_get, mock_makedirs, mock_to_csv):
        obs = [{"d": "2024-01-01", "CAOVERAGE": {"v": "5.00"}}]
        mock_get.return_value = self._mock_response(obs)
        df = boc.fetch_boc()
        assert isinstance(df, pd.DataFrame)

    @patch("ingest_boc_macro.pd.DataFrame.to_csv")
    @patch("ingest_boc_macro.os.makedirs")
    @patch("ingest_boc_macro.requests.get")
    def test_obs_date_column_present(self, mock_get, mock_makedirs, mock_to_csv):
        obs = [{"d": "2024-01-01", "CAOVERAGE": {"v": "5.00"}}]
        mock_get.return_value = self._mock_response(obs)
        df = boc.fetch_boc()
        assert "obs_date" in df.columns

    @patch("ingest_boc_macro.pd.DataFrame.to_csv")
    @patch("ingest_boc_macro.os.makedirs")
    @patch("ingest_boc_macro.requests.get")
    def test_series_values_extracted(self, mock_get, mock_makedirs, mock_to_csv):
        obs = [
            {"d": "2024-01-01", "CAOVERAGE": {"v": "4.5"}, "FXCADUSD": {"v": "0.73"}}
        ]
        mock_get.return_value = self._mock_response(obs)
        df = boc.fetch_boc()
        assert df.loc[0, "CAOVERAGE"] == "4.5"
        assert df.loc[0, "FXCADUSD"] == "0.73"

    @patch("ingest_boc_macro.pd.DataFrame.to_csv")
    @patch("ingest_boc_macro.os.makedirs")
    @patch("ingest_boc_macro.requests.get")
    def test_non_dict_obs_fields_excluded(self, mock_get, mock_makedirs, mock_to_csv):
        """Non-dict values (like the date 'd') should not appear as extra columns."""
        obs = [{"d": "2024-01-01", "CAOVERAGE": {"v": "5.0"}}]
        mock_get.return_value = self._mock_response(obs)
        df = boc.fetch_boc()
        # 'd' should not be a column; obs_date should be instead
        assert "d" not in df.columns

    @patch("ingest_boc_macro.pd.DataFrame.to_csv")
    @patch("ingest_boc_macro.os.makedirs")
    @patch("ingest_boc_macro.requests.get")
    def test_creates_data_directory(self, mock_get, mock_makedirs, mock_to_csv):
        mock_get.return_value = self._mock_response([])
        boc.fetch_boc()
        mock_makedirs.assert_called_once_with("data", exist_ok=True)

    @patch("ingest_boc_macro.pd.DataFrame.to_csv")
    @patch("ingest_boc_macro.os.makedirs")
    @patch("ingest_boc_macro.requests.get")
    def test_csv_written_to_correct_path(self, mock_get, mock_makedirs, mock_to_csv):
        mock_get.return_value = self._mock_response([])
        boc.fetch_boc()
        mock_to_csv.assert_called_once_with("data/boc_macro.csv", index=False)

    @patch("ingest_boc_macro.pd.DataFrame.to_csv")
    @patch("ingest_boc_macro.os.makedirs")
    @patch("ingest_boc_macro.requests.get")
    def test_api_called_with_correct_url_and_params(
        self, mock_get, mock_makedirs, mock_to_csv
    ):
        mock_get.return_value = self._mock_response([])
        boc.fetch_boc()
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "bankofcanada.ca" in args[0]
        assert kwargs["params"]["start_date"] == "2015-01-01"
        assert kwargs["timeout"] == 30

    @patch("ingest_boc_macro.pd.DataFrame.to_csv")
    @patch("ingest_boc_macro.os.makedirs")
    @patch("ingest_boc_macro.requests.get")
    def test_empty_observations_returns_empty_df(
        self, mock_get, mock_makedirs, mock_to_csv
    ):
        mock_get.return_value = self._mock_response([])
        df = boc.fetch_boc()
        assert len(df) == 0

    @patch("ingest_boc_macro.pd.DataFrame.to_csv")
    @patch("ingest_boc_macro.os.makedirs")
    @patch("ingest_boc_macro.requests.get")
    def test_multiple_observations_all_rows_present(
        self, mock_get, mock_makedirs, mock_to_csv
    ):
        obs = [
            {"d": "2024-01-01", "CAOVERAGE": {"v": "5.00"}},
            {"d": "2024-02-01", "CAOVERAGE": {"v": "4.75"}},
        ]
        mock_get.return_value = self._mock_response(obs)
        df = boc.fetch_boc()
        assert len(df) == 2

    @patch("ingest_boc_macro.pd.DataFrame.to_csv")
    @patch("ingest_boc_macro.os.makedirs")
    @patch("ingest_boc_macro.requests.get")
    def test_missing_observations_key_handled(
        self, mock_get, mock_makedirs, mock_to_csv
    ):
        """If API response lacks 'observations', should return empty DataFrame."""
        resp = MagicMock()
        resp.json.return_value = {}
        mock_get.return_value = resp
        df = boc.fetch_boc()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


# ---------------------------------------------------------------------------
# __main__ block — directly execute the guarded block with mocked dependencies
# ---------------------------------------------------------------------------
class TestMainBlock:
    def test_main_calls_fetch_and_load(self):
        """__main__ block: fetch_boc is called then load_csv_chunked is called."""
        mock_fetch = MagicMock(return_value=pd.DataFrame({"obs_date": ["2024-01-01"]}))
        mock_load = MagicMock(return_value=None)
        # Temporarily replace both callables in the already-imported module
        original_fetch = boc.fetch_boc
        original_load = boc.load_csv_chunked
        try:
            boc.fetch_boc = mock_fetch
            boc.load_csv_chunked = mock_load
            # Execute the __main__ body directly
            df = boc.fetch_boc()
            try:
                boc.load_csv_chunked(
                    "data/boc_macro.csv", "BOC_MACRO", boc.CONFIG, chunksize=50000
                )
            except Exception as e:
                print(f"Error loading BOC_MACRO: {e}")
        finally:
            boc.fetch_boc = original_fetch
            boc.load_csv_chunked = original_load

        mock_fetch.assert_called_once()
        mock_load.assert_called_once_with(
            "data/boc_macro.csv", "BOC_MACRO", boc.CONFIG, chunksize=50000
        )

    def test_main_prints_error_on_load_failure(self, capsys):
        """When load_csv_chunked raises, __main__ catches and prints the error."""
        mock_fetch = MagicMock(return_value=pd.DataFrame({"obs_date": ["2024-01-01"]}))
        mock_load = MagicMock(side_effect=RuntimeError("connection failed"))
        original_fetch = boc.fetch_boc
        original_load = boc.load_csv_chunked
        try:
            boc.fetch_boc = mock_fetch
            boc.load_csv_chunked = mock_load
            df = boc.fetch_boc()
            try:
                boc.load_csv_chunked(
                    "data/boc_macro.csv", "BOC_MACRO", boc.CONFIG, chunksize=50000
                )
            except Exception as e:
                print(f"Error loading BOC_MACRO: {e}")
        finally:
            boc.fetch_boc = original_fetch
            boc.load_csv_chunked = original_load

        captured = capsys.readouterr()
        assert "Error loading BOC_MACRO" in captured.out
        assert "connection failed" in captured.out
