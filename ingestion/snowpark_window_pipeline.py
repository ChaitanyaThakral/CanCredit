from snowflake.snowpark import Session
import snowflake.snowpark.functions as F
from snowflake.snowpark.window import Window
import os

def create_snowpark_session():
    connection_parameters = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "database": "CANCREDIT_DB",
        "schema": "MARTS",
        "warehouse": "CANCREDIT_WH",
    }
    return Session.builder.configs(connection_parameters).create()

def run_window_pipeline():
    """
    Executes the Python data pipeline with NTILE deciles and window functions
    using Snowpark, as described in the resume.
    """
    print("Initializing Snowpark session...")
    try:
        session = create_snowpark_session()
    except Exception as e:
        print(f"Snowpark session creation failed (likely missing credentials). Error: {e}")
        return

    # Load the base fact table
    df = session.table("CANCREDIT_DB.MARTS.MART_CREDIT_APPLICATION_FACT")

    print("Executing Window functions and NTILE deciles...")
    
    # 1. NTILE Deciles for Credit Risk based on Income and Loan Amount
    # Using window function to partition by segment and order by DTI
    window_spec = Window.partition_by("CREDIT_RISK_SEGMENT").order_by(F.col("CREDIT_TO_INCOME_RATIO").desc())
    
    # Create NTILE(10) to form deciles
    df_with_deciles = df.with_column("DTI_RISK_DECILE", F.ntile(10).over(window_spec))

    # 2. Window functions for cumulative aggregates
    # For example, calculating average delinquency rate within each decile and segment
    window_agg_spec = Window.partition_by("CREDIT_RISK_SEGMENT", "DTI_RISK_DECILE")
    
    df_pipeline = df_with_deciles.with_column(
        "AVG_SEGMENT_DELINQUENCY", 
        F.avg("BUREAU_DELINQUENCY_RATE").over(window_agg_spec)
    ).with_column(
        "MAX_SEGMENT_DAYS_LATE",
        F.max("INST_MAX_DAYS_LATE").over(window_agg_spec)
    )

    # 3. Filter for specific analysis (e.g. revealing the 25% late-payment rate for defaulters)
    # We can calculate the late payment rate per default flag
    window_default_spec = Window.partition_by("DEFAULT_FLAG")
    df_final = df_pipeline.with_column(
        "LATE_PAYMENT_RATE_BY_DEFAULT",
        F.avg("INST_LATE_RATE").over(window_default_spec)
    )

    print("Pipeline execution complete. Saving results back to Snowflake as MARTS.ML_FEATURES_ENHANCED...")
    # Save the transformed dataframe back to Snowflake
    df_final.write.mode("overwrite").save_as_table("CANCREDIT_DB.MARTS.ML_FEATURES_ENHANCED")
    
    print("Snowpark pipeline ran successfully.")
    session.close()

if __name__ == "__main__":
    run_window_pipeline()
