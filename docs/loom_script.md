# CanCredit Loom Demo Script

This script is designed to help you record a 5-minute portfolio demo highlighting your work across Data Engineering, Data Science, and Business Analysis.

## Demo Script (5 Minutes)

**[0:00–0:40] Airflow Orchestration & Pipeline**
*(Screen: Airflow UI showing the `cancredit_pipeline` DAG)*
> "This is the Airflow UI showing the `cancredit_pipeline` DAG. You can see the full chain: raw validation, dbt staging, dbt intermediate (which aggregates 58 million rows down to 307K applicant-level features), dbt marts, and finally the Great Expectations data quality check. This runs automatically every weekday morning."

**[0:40–1:30] dbt Transformation & Lineage**
*(Screen: dbt docs lineage graph)*
> "Here's the dbt docs lineage graph. 8 source tables feed 8 staging models, which feed 4 intermediate aggregation models, which feed 3 mart tables and the ML feature store. Every model has column descriptions and automated tests. The snapshot model implements SCD Type 2 tracking for risk segment changes."

**[1:30–2:30] Machine Learning & MLflow Tracking**
*(Screen: MLflow UI showing experiments and SHAP artifact)*
> "Here's the MLflow UI showing two experiments — a Logistic Regression baseline at AUC 0.72, and the final XGBoost model at AUC 0.78. The Gini coefficient is 0.56, which is within the range of production credit models at major Canadian banks. I also logged SHAP feature importances as an artifact — `EXT_SOURCE_2` is the strongest predictor, consistent with credit scoring industry practice."

**[2:30–3:30] FastAPI Scoring API**
*(Screen: FastAPI Swagger UI at `localhost:8000/docs`, showing a live POST request)*
> "Here's the FastAPI scoring endpoint. I POST a loan application and get back a default probability, a risk tier — LOW, MEDIUM, HIGH, or VERY_HIGH — a lending decision, and the top 3 risk drivers from SHAP. Responses under Redis cache hit in about 10ms."

**[3:30–5:00] Power BI Dashboard & Business Recommendations**
*(Screen: Power BI Dashboard pages)*
> "Here's the Power BI dashboard. Page 1 is the executive portfolio overview — KPI cards for default rate, portfolio value, average DTI. Page 2 is the risk factor deep dive — this scatter plot shows the correlation between DTI and bureau delinquency rate, coloured by actual default outcome. Page 4 is my business narrative page with five actionable recommendations framed for a risk committee audience."
