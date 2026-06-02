"""
load_raw_to_snowflake.py
Loads all Home Credit CSV files into Snowflake RAW schema using write_pandas.
Runs chunked so we don't OOM on large files.
"""
import os, sys
from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
import warnings
warnings.filterwarnings("ignore")

SNOWFLAKE_CFG = {
    "account":   os.getenv("SNOWFLAKE_ACCOUNT", "").strip(),
    "user":      os.getenv("SNOWFLAKE_USER", "").strip(),
    "password":  os.getenv("SNOWFLAKE_PASSWORD", "").strip(),
    "database":  "CANCREDIT_DB",
    "schema":    "RAW",
    "warehouse": "CANCREDIT_WH",
}

TABLES = {
    "APPLICATION_TRAIN":       "data/home-credit/application_train.csv",
    "APPLICATION_TEST":        "data/home-credit/application_test.csv",
    "BUREAU":                  "data/home-credit/bureau.csv",
    "BUREAU_BALANCE":          "data/home-credit/bureau_balance.csv",
    "PREVIOUS_APPLICATION":    "data/home-credit/previous_application.csv",
    "POS_CASH_BALANCE":        "data/home-credit/POS_CASH_balance.csv",
    "INSTALLMENTS_PAYMENTS":   "data/home-credit/installments_payments.csv",
    "CREDIT_CARD_BALANCE":     "data/home-credit/credit_card_balance.csv",
}

CHUNK_SIZE = 100_000

def snowflake_type(dtype):
    s = str(dtype)
    if "int" in s:   return "NUMBER"
    if "float" in s: return "FLOAT"
    return "VARCHAR(1024)"

def create_table(cur, table, df):
    cols = ", ".join(f'"{c.upper()}" {snowflake_type(d)}' for c, d in df.dtypes.items())
    cur.execute(f"DROP TABLE IF EXISTS CANCREDIT_DB.RAW.{table}")
    cur.execute(f"CREATE TABLE CANCREDIT_DB.RAW.{table} ({cols})")

def load_table(table, filepath):
    if not os.path.exists(filepath):
        print(f"  SKIP: {filepath} not found")
        return

    conn = snowflake.connector.connect(**SNOWFLAKE_CFG)
    cur  = conn.cursor()

    total = 0
    first = True
    for i, chunk in enumerate(pd.read_csv(filepath, chunksize=CHUNK_SIZE)):
        chunk.columns = [c.upper() for c in chunk.columns]
        if first:
            create_table(cur, table, chunk)
            first = False
        success, nchunks, nrows, _ = write_pandas(
            conn, chunk, table,
            database="CANCREDIT_DB", schema="RAW",
            overwrite=False
        )
        total += nrows
        print(f"  chunk {i+1}: {nrows:,} rows  (running total: {total:,})", flush=True)

    print(f"  DONE: {table} — {total:,} rows loaded\n")
    conn.close()

if __name__ == "__main__":
    # Allow running a single table: python load_raw.py BUREAU
    target = sys.argv[1].upper() if len(sys.argv) > 1 else None
    for table, path in TABLES.items():
        if target and table != target:
            continue
        print(f"\nLoading {table}...")
        try:
            load_table(table, path)
        except Exception as e:
            print(f"  ERROR loading {table}: {e}\n")
