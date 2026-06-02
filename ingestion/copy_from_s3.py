import os
import snowflake.connector
from dotenv import load_dotenv
load_dotenv()

def get_snowflake_conn():
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT", ""),
        user=os.getenv("SNOWFLAKE_USER", ""),
        password=os.getenv("SNOWFLAKE_PASSWORD", ""),
        database="CANCREDIT_DB",
        schema="RAW",
        warehouse="CANCREDIT_WH",
    )

TABLES = [
    "APPLICATION_TRAIN",
    "APPLICATION_TEST",
    "BUREAU",
    "BUREAU_BALANCE",
    "PREVIOUS_APPLICATION",
    "POS_CASH_BALANCE",
    "INSTALLMENTS_PAYMENTS",
    "CREDIT_CARD_BALANCE",
]

bucket_name = os.getenv("CANCREDIT_S3_BUCKET", "cancredit-raw-data-bucket")
aws_key = os.getenv("AWS_ACCESS_KEY_ID", "")
aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY", "")

def run_copy():
    conn = get_snowflake_conn()
    cur = conn.cursor()
    
    # Recreate stage to ensure error_on_column_count_mismatch is false
    stage_sql = f"""
    CREATE OR REPLACE STAGE cancredit_s3_stage
    URL='s3://{bucket_name}/raw/'
    CREDENTIALS=(AWS_KEY_ID='{aws_key}' AWS_SECRET_KEY='{aws_secret}')
    FILE_FORMAT=(TYPE=CSV FIELD_OPTIONALLY_ENCLOSED_BY='"' SKIP_HEADER=1 ERROR_ON_COLUMN_COUNT_MISMATCH=FALSE)
    """
    cur.execute(stage_sql)
    print("Stage updated with ERROR_ON_COLUMN_COUNT_MISMATCH=FALSE.")
    
    for table in TABLES:
        # For POS_CASH_BALANCE the file name case is POS_CASH_balance.csv
        file_name = f"{table.lower()}.csv"
        if table == "POS_CASH_BALANCE":
            file_name = "POS_CASH_balance.csv"
            
        print(f"Executing COPY INTO for {table}...")
        copy_sql = f"""
        COPY INTO CANCREDIT_DB.RAW.{table}
        FROM @cancredit_s3_stage/{file_name}
        ON_ERROR = 'CONTINUE'
        """
        try:
            cur.execute(copy_sql)
            res = cur.fetchall()
            print(f"  Result: {res}")
        except Exception as e:
            print(f"  Error on {table}: {e}")
            
    conn.close()

if __name__ == "__main__":
    run_copy()
