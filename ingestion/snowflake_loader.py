import snowflake.connector
import pandas as pd
from snowflake.connector.pandas_tools import write_pandas

def get_snowflake_conn(config: dict):
    return snowflake.connector.connect(
        account=config['account'], user=config['user'],
        password=config['password'], database='CANCREDIT_DB',
        schema='RAW', warehouse='CANCREDIT_WH'
    )

def infer_ddl(df: pd.DataFrame, table: str) -> str:
    type_map = {
        'int64': 'NUMBER', 'float64': 'FLOAT',
        'object': 'VARCHAR(500)', 'bool': 'BOOLEAN',
        'datetime64[ns]': 'TIMESTAMP_NTZ'
    }
    cols = ", ".join([
        f'"{c.upper()}" {type_map.get(str(d), "VARCHAR(500)")}'
        for c, d in df.dtypes.items()
    ])
    return f"CREATE TABLE IF NOT EXISTS {table} ({cols})"

def load_csv_chunked(filepath: str, table: str, config: dict, chunksize: int = 500_000):
    conn = get_snowflake_conn(config)
    cursor = conn.cursor()
    for i, chunk in enumerate(pd.read_csv(filepath, chunksize=chunksize)):
        chunk['LOADED_AT'] = pd.Timestamp.now()
        if i == 0:
            cursor.execute(f"DROP TABLE IF EXISTS CANCREDIT_DB.RAW.{table}")
            cursor.execute(infer_ddl(chunk, f"CANCREDIT_DB.RAW.{table}"))
        write_pandas(conn, chunk, table,
                     database='CANCREDIT_DB', schema='RAW',
                     overwrite=False)
        print(f"  Chunk {i+1}: {len(chunk):,} rows loaded into {table}")
    conn.close()
