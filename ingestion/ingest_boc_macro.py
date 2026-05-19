import requests
import pandas as pd
import os
from snowflake_loader import load_csv_chunked

CONFIG = {
    'account': os.environ.get('SNOWFLAKE_ACCOUNT', ''),
    'user': os.environ.get('SNOWFLAKE_USER', ''),
    'password': os.environ.get('SNOWFLAKE_PASSWORD', '')
}

def fetch_boc():
    # Series: overnight rate, 2yr bond, 10yr bond, CAD/USD, CPI
    series = ['CAOVERAGE', 'AUCAUSBOND2Y', 'AUCAUSBOND10Y', 'FXCADUSD', 'CPIALL']
    url = "https://www.bankofcanada.ca/valet/observations/group/bond_yields_all_en/json"
    params = {'start_date': '2015-01-01'}
    resp = requests.get(url, params=params, timeout=30)
    data = resp.json()
    rows = []
    for obs in data.get('observations', []):
        row = {'obs_date': obs['d']}
        for k, v in obs.items():
            if k != 'd' and isinstance(v, dict):
                row[k] = v.get('v')
        rows.append(row)
    df = pd.DataFrame(rows)
    
    os.makedirs('data', exist_ok=True)
    df.to_csv('data/boc_macro.csv', index=False)
    return df

if __name__ == "__main__":
    df = fetch_boc()
    try:
        load_csv_chunked('data/boc_macro.csv', 'BOC_MACRO', CONFIG, chunksize=50000)
    except Exception as e:
        print(f"Error loading BOC_MACRO: {e}")
