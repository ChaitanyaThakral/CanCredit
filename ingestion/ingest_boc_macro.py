"""
ingestion/ingest_boc_macro.py — Bank of Canada macro data ingestion.

Fetches 5 key series from the BOC Valet API (no API key required):
  - CAOVERAGE  : Bank of Canada overnight rate target
  - BD.CDN.2YR.DQ.YLD : 2-year Government of Canada bond yield
  - BD.CDN.10YR.DQ.YLD: 10-year Government of Canada bond yield
  - FXCADUSD   : CAD/USD exchange rate
  - STATIC_TOTALCPICHANGE: CPI total change (YoY %)

Data goes back to 2015 — the start of the Home Credit application dataset window.

Usage:
    cd ingestion
    python ingest_boc_macro.py
"""

import os
import sys
import time
import requests
import pandas as pd

# Allow running from project root or ingestion/
sys.path.insert(0, os.path.dirname(__file__))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from snowflake_loader import get_snowflake_conn, infer_ddl
from snowflake.connector.pandas_tools import write_pandas

CONFIG = {
    "account":  os.environ.get("SNOWFLAKE_ACCOUNT", ""),
    "user":     os.environ.get("SNOWFLAKE_USER", ""),
    "password": os.environ.get("SNOWFLAKE_PASSWORD", ""),
}

# ── BOC Valet API series ──────────────────────────────────────────────────────
# Series IDs confirmed against https://www.bankofcanada.ca/valet/lists/series/json
BOC_SERIES = {
    "CAOVERAGE":               "overnight_rate",
    "BD.CDN.2YR.DQ.YLD":      "bond_2yr",
    "BD.CDN.10YR.DQ.YLD":     "bond_10yr",
    "FXCADUSD":                "cadusd",
    "STATIC_TOTALCPICHANGE":   "cpi_total",
}

BASE_URL    = "https://www.bankofcanada.ca/valet/observations"
START_DATE  = "2015-01-01"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "boc_macro.csv")


def fetch_series(series_id: str, start_date: str) -> pd.DataFrame:
    """Fetch a single BOC Valet series and return a tidy DataFrame."""
    url = f"{BASE_URL}/{series_id}/json"
    params = {"start_date": start_date, "order_dir": "asc"}

    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            break
        except (requests.RequestException, ValueError) as e:
            if attempt == 2:
                print(f"    ⚠️  Failed to fetch {series_id} after 3 attempts: {e}")
                return pd.DataFrame(columns=["date", series_id])
            time.sleep(2 ** attempt)

    observations = data.get("observations", [])
    rows = []
    for obs in observations:
        val = obs.get(series_id, {})
        rows.append({
            "date":     obs["d"],
            series_id:  val.get("v") if isinstance(val, dict) else None,
        })
    return pd.DataFrame(rows)


def fetch_boc(start_date: str = START_DATE) -> pd.DataFrame:
    """
    Fetch all BOC macro series and merge into a single wide DataFrame.
    Returns one row per business day with columns:
        date, overnight_rate, bond_2yr, bond_10yr, cadusd, cpi_total
    """
    print(f" Fetching BOC macro series (start: {start_date})...")
    frames = []

    for series_id, col_name in BOC_SERIES.items():
        print(f"    Fetching {series_id} → {col_name}...", end=" ")
        df_s = fetch_series(series_id, start_date)

        if df_s.empty or series_id not in df_s.columns:
            print("⚠️  empty")
            continue

        df_s = df_s.rename(columns={series_id: col_name})
        df_s[col_name] = pd.to_numeric(df_s[col_name], errors="coerce")
        frames.append(df_s.set_index("date"))
        print(f"✅ {len(df_s):,} rows")

    if not frames:
        raise RuntimeError("No BOC series data could be fetched. Check your internet connection.")

    # Outer join on date so we keep all dates even if some series are missing for that date
    df = frames[0]
    for frame in frames[1:]:
        df = df.join(frame, how="outer")

    df = df.reset_index().rename(columns={"index": "date"})
    df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)
    df = df.sort_values("date").reset_index(drop=True)

    print(f"\n✅ Combined dataset: {len(df):,} rows × {len(df.columns)} columns")
    print(f"   Date range: {df['date'].min()} → {df['date'].max()}")
    print(f"   Null rates:\n{df.isnull().mean().round(3)}")

    return df


def save_csv(df: pd.DataFrame, path: str = OUTPUT_PATH) -> str:
    """Save DataFrame to CSV for Snowflake internal stage upload."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)
    print(f"\n💾 Saved to {path} ({os.path.getsize(path) / 1024:.1f} KB)")
    return path


def load_to_snowflake(df: pd.DataFrame) -> None:
    """Load BOC macro DataFrame directly into Snowflake RAW.BOC_MACRO."""
    print("\n🔼 Loading to Snowflake RAW.BOC_MACRO...")

    # Uppercase columns for Snowflake convention
    df_up = df.copy()
    df_up.columns = [c.upper() for c in df_up.columns]
    df_up["LOADED_AT"] = pd.Timestamp.now()

    conn = get_snowflake_conn(CONFIG)
    cur  = conn.cursor()

    try:
        # Drop + recreate on full historical load
        cur.execute("DROP TABLE IF EXISTS CANCREDIT_DB.RAW.BOC_MACRO")
        cur.execute(infer_ddl(df_up, "CANCREDIT_DB.RAW.BOC_MACRO"))
        success, nchunks, nrows, _ = write_pandas(
            conn, df_up, "BOC_MACRO",
            database="CANCREDIT_DB", schema="RAW",
            overwrite=False
        )
        print(f"✅ Loaded {nrows:,} rows into CANCREDIT_DB.RAW.BOC_MACRO")
    finally:
        conn.close()


if __name__ == "__main__":
    df = fetch_boc(start_date=START_DATE)
    save_csv(df)
    try:
        load_to_snowflake(df)
    except Exception as exc:
        print(f"\n⚠️  Snowflake load error: {exc}")
        print("   CSV saved to /data/boc_macro.csv — upload manually if needed.")
