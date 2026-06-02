import snowflake.connector
import pandas as pd
import boto3
import os

def get_snowflake_conn(config: dict):
    return snowflake.connector.connect(
        account=config["account"],
        user=config["user"],
        password=config["password"],
        database="CANCREDIT_DB",
        schema="RAW",
        warehouse="CANCREDIT_WH",
    )

def infer_ddl(df: pd.DataFrame, table: str) -> str:
    type_map = {
        "int64": "NUMBER",
        "float64": "FLOAT",
        "object": "VARCHAR(500)",
        "bool": "BOOLEAN",
        "datetime64[ns]": "TIMESTAMP_NTZ",
    }
    cols = ", ".join(
        [
            f'"{c.upper()}" {type_map.get(str(d), "VARCHAR(500)")}'
            for c, d in df.dtypes.items()
        ]
    )
    # Add load timestamp
    cols += ', "LOADED_AT" TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()'
    return f"CREATE TABLE IF NOT EXISTS {table} ({cols})"

def upload_to_s3(filepath: str, bucket: str, s3_key: str):
    print(f"Uploading {filepath} to s3://{bucket}/{s3_key}...")
    s3_client = boto3.client("s3")
    s3_client.upload_file(filepath, bucket, s3_key)
    print("Upload complete.")

def load_csv_via_s3(filepath: str, table: str, config: dict):
    """
    AWS S3 -> Snowflake COPY INTO pipeline implementation.
    Requires AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in environment.
    """
    bucket_name = os.getenv("CANCREDIT_S3_BUCKET", "cancredit-raw-data-bucket")
    file_name = os.path.basename(filepath)
    s3_key = f"raw/{file_name}"
    
    # 1. Upload to S3
    try:
        upload_to_s3(filepath, bucket_name, s3_key)
    except Exception as e:
        print(f"Warning: S3 upload failed (AWS credentials might be missing). Proceeding with Snowflake commands assuming data exists in S3. Error: {e}")

    # 2. Snowflake COPY INTO
    conn = get_snowflake_conn(config)
    cursor = conn.cursor()
    
    # Infer DDL by reading just the first 100 rows locally
    df_sample = pd.read_csv(filepath, nrows=100)
    full_table_name = f"CANCREDIT_DB.RAW.{table}"
    
    cursor.execute(f"DROP TABLE IF EXISTS {full_table_name}")
    cursor.execute(infer_ddl(df_sample, full_table_name))
    
    # Create external stage (assuming storage integration or credentials exist in Snowflake)
    # Note: In a real prod environment, use a STORAGE INTEGRATION instead of hardcoding credentials,
    # but for resume demo, we use AWS_KEY_ID if available, or just standard stage creation.
    aws_key = os.getenv("AWS_ACCESS_KEY_ID", "dummy_key")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY", "dummy_secret")
    
    stage_sql = f"""
    CREATE OR REPLACE STAGE cancredit_s3_stage
    URL='s3://{bucket_name}/raw/'
    CREDENTIALS=(AWS_KEY_ID='{aws_key}' AWS_SECRET_KEY='{aws_secret}')
    FILE_FORMAT=(TYPE=CSV FIELD_OPTIONALLY_ENCLOSED_BY='"' SKIP_HEADER=1)
    """
    cursor.execute(stage_sql)
    
    # Execute COPY INTO
    # We match columns by position or name. Since CSV lacks the LOADED_AT column, we specify it or rely on default.
    copy_sql = f"""
    COPY INTO {full_table_name}
    FROM @cancredit_s3_stage/{file_name}
    ON_ERROR = 'CONTINUE'
    """
    print(f"Executing COPY INTO for {table}...")
    cursor.execute(copy_sql)
    result = cursor.fetchall()
    print(f"COPY INTO Result: {result}")
    
    conn.close()

# For backward compatibility with any other scripts calling load_csv_chunked
def load_csv_chunked(filepath: str, table: str, config: dict, chunksize: int = 500_000):
    load_csv_via_s3(filepath, table, config)
