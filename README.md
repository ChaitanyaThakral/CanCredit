# CanCredit Platform

This repository contains the architecture, ingestion, and machine learning pipeline for the CanCredit platform.

## Architecture Diagram

```mermaid
flowchart TD
    subgraph External Sources
        HC[Home Credit Kaggle 58M rows]
        BOC[Bank of Canada API]
    end

    subgraph Orchestration
        Airflow[Airflow DAGs]
    end

    subgraph CI/CD
        GH[GitHub Actions CI<br>main branch]
    end

    subgraph Data Warehouse (Snowflake)
        RAW[Snowflake RAW]
        STG[Snowflake STAGING]
        INT[Snowflake INTERMEDIATE]
        MART[Snowflake MARTS]
        MLF[Snowflake ML_FEATURES]
    end

    subgraph Transformations & Validation
        DBT_STG[dbt staging]
        DBT_INT[dbt intermediate]
        DBT_MART[dbt marts]
        DBT_MLF[dbt ml_features]
        GE[Great Expectations]
        DBT_TEST[dbt test on every PR]
    end

    subgraph Analytics & ML
        PBI[Power BI Dashboard]
        XGB[Python XGBoost + MLflow]
        API[REST Scoring API /predict (FastAPI)]
        MODEL[Trained Model]
    end

    %% Ingestion
    HC --> |Python chunked loader| RAW
    BOC --> |Python chunked loader| RAW

    %% Orchestration
    Airflow --> |orchestrates pipeline| DBT_STG
    
    %% Transformations
    RAW --> DBT_STG
    DBT_STG --> STG
    STG --> DBT_INT
    DBT_INT --> INT
    INT --> DBT_MART
    DBT_MART --> MART
    MART --> DBT_MLF
    DBT_MLF --> MLF

    %% Validation
    GE -.-> |validates mart tables| MART
    DBT_TEST -.-> STG

    %% Consumption
    MART --> |DirectQuery| PBI
    MLF --> XGB
    XGB --> MODEL
    MODEL --> API
```
