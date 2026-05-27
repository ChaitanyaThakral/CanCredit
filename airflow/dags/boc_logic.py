"""
boc_logic.py — Pure Python business logic extracted from the BOC DAG.
No Airflow imports here, so this module is fully unit-testable without
an Airflow installation.  The DAG imports these functions directly.
"""
import requests
import pandas as pd


def fetch_latest_boc(last_date: str, output_path: str = '/tmp/boc_latest.csv') -> int:
    """
    Fetch BOC observations since `last_date` and write them to `output_path`.

    Args:
        last_date:   ISO date string (YYYY-MM-DD) for API start_date param.
        output_path: Local CSV destination (default: /tmp/boc_latest.csv).

    Returns:
        Number of observation rows fetched.
    """
    url = "https://www.bankofcanada.ca/valet/observations/group/bond_yields_all_en/json"
    resp = requests.get(url, params={'start_date': last_date}, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    rows = [
        {
            'obs_date': o['d'],
            **{k: v.get('v') for k, v in o.items() if k != 'd' and isinstance(v, dict)}
        }
        for o in data.get('observations', [])
    ]
    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)
    return len(df)


def branch_on_rows(row_count) -> str:
    """
    Return the downstream task_id to execute based on row count.

    Args:
        row_count: Number of rows returned by fetch_latest_boc (from XCom).

    Returns:
        'load_boc' if there is new data, 'skip_boc' otherwise.
    """
    return 'load_boc' if row_count and row_count > 0 else 'skip_boc'
