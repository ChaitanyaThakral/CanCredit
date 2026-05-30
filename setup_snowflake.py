"""
setup_snowflake.py — One-time Snowflake environment bootstrap.

Creates:
  - CANCREDIT_WH warehouse (X-Small, auto-suspend 60s)
  - CANCREDIT_DB database
  - All 6 schemas: RAW, STAGING, INTERMEDIATE, MARTS, ML_FEATURES, SNAPSHOTS
  - Internal stage for BOC macro data ingestion
  - Snowflake DQ Alert on the mart fact table

Usage:
    cp .env.example .env          # Fill in your credentials
    python setup_snowflake.py
"""

import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv optional — env vars can be set directly

import snowflake.connector

# ── Credentials ───────────────────────────────────────────────────────────────
ACCOUNT  = os.getenv("SNOWFLAKE_ACCOUNT", "").strip()
USER     = os.getenv("SNOWFLAKE_USER", "").strip()
PASSWORD = os.getenv("SNOWFLAKE_PASSWORD", "").strip()

if not all([ACCOUNT, USER, PASSWORD]):
    print("ERROR: Set SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD in .env")
    sys.exit(1)

conn = snowflake.connector.connect(
    account=ACCOUNT,
    user=USER,
    password=PASSWORD,
)
cur = conn.cursor()

print("🏗  Setting up CanCredit Snowflake infrastructure...\n")

DDL_STATEMENTS = [
    # ── Warehouse ──────────────────────────────────────────────────────────
    ("Warehouse",
     """CREATE WAREHOUSE IF NOT EXISTS CANCREDIT_WH
        WITH WAREHOUSE_SIZE = 'X-SMALL'
             AUTO_SUSPEND    = 60
             AUTO_RESUME     = TRUE
             COMMENT         = 'CanCredit analytics warehouse'"""),

    # ── Database ───────────────────────────────────────────────────────────
    ("Database",
     "CREATE DATABASE IF NOT EXISTS CANCREDIT_DB COMMENT = 'CanCredit credit risk platform'"),

    # ── Schemas (medallion architecture) ──────────────────────────────────
    ("Schema RAW",
     "CREATE SCHEMA IF NOT EXISTS CANCREDIT_DB.RAW COMMENT = 'Bronze layer — raw ingested data'"),
    ("Schema STAGING",
     "CREATE SCHEMA IF NOT EXISTS CANCREDIT_DB.STAGING COMMENT = 'Silver layer — dbt staging views'"),
    ("Schema INTERMEDIATE",
     "CREATE SCHEMA IF NOT EXISTS CANCREDIT_DB.INTERMEDIATE COMMENT = 'Silver+ layer — applicant-level aggregations'"),
    ("Schema MARTS",
     "CREATE SCHEMA IF NOT EXISTS CANCREDIT_DB.MARTS COMMENT = 'Gold layer — star schema fact/dim tables'"),
    ("Schema ML_FEATURES",
     "CREATE SCHEMA IF NOT EXISTS CANCREDIT_DB.ML_FEATURES COMMENT = 'Gold layer — ML feature store'"),
    ("Schema SNAPSHOTS",
     "CREATE SCHEMA IF NOT EXISTS CANCREDIT_DB.SNAPSHOTS COMMENT = 'SCD Type 2 snapshot history'"),

    # ── Use warehouse for subsequent commands ──────────────────────────────
    ("Use warehouse",
     "USE WAREHOUSE CANCREDIT_WH"),

    # ── Internal stage for BOC macro CSV uploads ───────────────────────────
    ("Stage BOC_STAGE",
     """CREATE STAGE IF NOT EXISTS CANCREDIT_DB.RAW.BOC_STAGE
        FILE_FORMAT = (
            TYPE                        = 'CSV'
            FIELD_OPTIONALLY_ENCLOSED_BY = '"'
            SKIP_HEADER                 = 1
            NULL_IF                     = ('', 'NULL', 'null')
            EMPTY_FIELD_AS_NULL         = TRUE
        )
        COMMENT = 'Internal stage for Bank of Canada macro data CSV uploads'"""),
]

for label, sql in DDL_STATEMENTS:
    try:
        cur.execute(sql)
        print(f"  ✅ {label}")
    except Exception as e:
        print(f"  ⚠️  {label}: {e}")

# ── Snowflake Data Quality Alert ─────────────────────────────────────────────
# Note: Alerts require email notifications to be configured in your Snowflake account.
# If SYSTEM$SEND_EMAIL is not available, the alert is created but notification silently skipped.
print("\n🔔 Configuring Data Quality Alert...")

DQ_ALERT_SQL = """
CREATE OR REPLACE ALERT CANCREDIT_DB.MARTS.CANCREDIT_DQ_ALERT
    WAREHOUSE = CANCREDIT_WH
    SCHEDULE  = 'USING CRON 0 8 * * 1-5 America/Toronto'
    IF (EXISTS (
        SELECT 1
        FROM CANCREDIT_DB.MARTS.MART_CREDIT_APPLICATION_FACT
        WHERE credit_to_income_ratio < 0
           OR bureau_delinquency_rate > 1
           OR default_flag NOT IN (0, 1)
           OR composite_risk_score < 0
           OR composite_risk_score > 1
        LIMIT 1
    ))
    THEN CALL SYSTEM$SEND_EMAIL(
        'admin@cancredit.local',
        'CanCredit DQ Alert — mart_credit_application_fact',
        'One or more data quality checks FAILED on MART_CREDIT_APPLICATION_FACT. '
        'Check the Snowflake alert history for details.'
    )
"""

try:
    cur.execute(DQ_ALERT_SQL)
    # Alert must be explicitly resumed after creation
    cur.execute("ALTER ALERT CANCREDIT_DB.MARTS.CANCREDIT_DQ_ALERT RESUME")
    print("  ✅ DQ Alert created and resumed")
except Exception as e:
    print(f"  ⚠️  DQ Alert (requires mart table to exist — run dbt first): {e}")

conn.close()

print("\n══════════════════════════════════════════════")
print(" CanCredit Snowflake setup complete!")
print("══════════════════════════════════════════════")
print("\nNext steps:")
print("  1. Download Kaggle datasets to /data/")
print("  2. Run: python ingestion/load_all.py")
print("  3. Run: python ingestion/ingest_boc_macro.py")
print("  4. Run: cd dbt/cancredit && dbt deps && dbt run && dbt test")
print("  5. Run: python model/train.py")
print("  6. Run: uvicorn api.main:app --reload")
