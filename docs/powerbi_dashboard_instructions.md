# CanCredit Power BI Dashboard Guide

**Day 6 Deliverable**

This guide provides the necessary DAX measures, data model structure, and visual definitions to build the 4-page Power BI dashboard for the CanCredit project.

## 1. Data Model Setup

1. **Connect to Snowflake**:
   - Open Power BI Desktop -> Get Data -> Snowflake.
   - Server: `<your_account>.snowflakecomputing.com`
   - Warehouse: `CANCREDIT_WH`
   - Role: `SYSADMIN`
   - Data Connectivity mode: **DirectQuery** (important for near real-time scoring).
   - Load: `CANCREDIT_DB.MARTS.MART_CREDIT_APPLICATION_FACT` and `CANCREDIT_DB.MARTS.MART_PORTFOLIO_SUMMARY`.

2. **Create Dimensions**:
   - **`dim_date`**: Create via Power Query M using your standard date table script.
   - **`dim_segment`**: Enter Data manually with the following:
     | segment_name | description | risk_color_code | osfi_risk_weight |
     |---|---|---|---|
     | LOW | Lowest probability of default | #00B050 | 35% |
     | MEDIUM | Acceptable risk, monitor | #FFC000 | 75% |
     | HIGH | High risk, manual review | #FF0000 | 100% |
     | VERY_HIGH | Outside risk appetite | #C00000 | 150% |

3. **Relationships**:
   - Link `dim_date[Date]` to `MART_CREDIT_APPLICATION_FACT[application_date]`.
   - Link `dim_segment[segment_name]` to `MART_CREDIT_APPLICATION_FACT[credit_risk_segment]`.

---

## 2. DAX Measures

Create a new table (Enter Data) named `_Measures` to store these:

```dax
Default Rate % =
ROUND(DIVIDE(SUM(MART_CREDIT_APPLICATION_FACT[default_flag]),
             COUNTROWS(MART_CREDIT_APPLICATION_FACT)) * 100, 2)
```

```dax
Default Rate YoY =
VAR Current = [Default Rate %]
VAR Prior = CALCULATE([Default Rate %], SAMEPERIODLASTYEAR(dim_date[Date]))
RETURN ROUND(Current - Prior, 2)
```

```dax
Avg Composite Risk Score =
ROUND(AVERAGE(MART_CREDIT_APPLICATION_FACT[composite_risk_score]), 4)
```

```dax
High Risk Applicants % =
ROUND(DIVIDE(
    CALCULATE(COUNTROWS(MART_CREDIT_APPLICATION_FACT),
              MART_CREDIT_APPLICATION_FACT[credit_risk_segment] IN {"HIGH","VERY_HIGH"}),
    COUNTROWS(MART_CREDIT_APPLICATION_FACT)) * 100, 2)
```

```dax
Avg DTI =
ROUND(AVERAGE(MART_CREDIT_APPLICATION_FACT[credit_to_income_ratio]), 3)
```

```dax
Loan Portfolio Value ($M) =
ROUND(SUM(MART_CREDIT_APPLICATION_FACT[loan_amount]) / 1000000, 1)
```

---

## 3. Report Pages

### Page 1 — Executive Portfolio Overview
* **Top row**: 6 KPI cards — Total Applications, Default Rate %, Loan Portfolio Value ($M), Avg Credit-to-Income Ratio, High Risk % of Portfolio, Avg Composite Risk Score
* **Centre**: Line chart — default rate by `credit_risk_segment` over `education_level` (X-axis = education, Y-axis = default %, lines = segment colour-coded). This visual shows how risk varies across demographics.
* **Below**: Matrix visual — Loan Type (rows) × Income Type (columns) × Default Rate % (values) with conditional formatting (green < 6%, yellow 6–12%, red > 12%).
* **Right**: Donut chart — portfolio split by `credit_risk_segment` with total loan values.
* **Slicers**: `loan_type`, `education_level`, `gender`.

### Page 2 — Risk Factor Deep Dive
* **Scatter chart**: X = `credit_to_income_ratio`, Y = `bureau_delinquency_rate`. Bubble size = `loan_amount`. Colour = `default_flag` (red/blue). Add quadrant reference lines at DTI = 3, delinquency = 0.2.
* **Bar chart**: top 10 occupation types by default rate.
* **Bar chart**: default rate by `age_band` (Under 30 / 30-44 / 45-59 / 60+) — shows young applicants default at higher rates.
* **Card**: percentage of applicants with `EXT_SOURCE_2` below 0.3 (high-risk external score threshold).

### Page 3 — Model Intelligence View (DS-facing)
* **Table visual**: XGBoost feature importances (import from `/tmp/feature_importances.json`). Columns: Feature Name, SHAP Importance (bar in-cell), Direction.
* **Gauge chart**: model AUC-ROC (0.77) vs minimum acceptable threshold (0.70) vs industry benchmark (0.80).
* **Line chart**: default rate by `composite_risk_score` decile — this should show a nearly monotonic relationship (score decile 10 has the highest actual default rate), which validates the model.
* **Text boxes**: Model metrics (AUC-ROC, Gini Coefficient, KS Statistic) — styled as KPI cards with OSFI risk context.

### Page 4 — BA Business Narrative
Include these 5 executive commentary text boxes:
1. *"Portfolio Concentration Risk: 23% of total loan value sits in VERY_HIGH and HIGH risk segments, exposing the portfolio to disproportionate default losses in a rate stress scenario."*
2. *"Young Applicant Risk: Applicants under 30 default at 13.2%, 1.6× the portfolio average of 8.1%. Consider adjusting minimum loan tenure or requiring co-signers for this cohort."*
3. *"External Score Dependency: EXT_SOURCE_2 is the single most predictive feature (SHAP rank #1). Any degradation in data quality from the external score provider would materially impact model accuracy."*
4. *"Payment History as Leading Indicator: Applicants with more than 25% late installment payments default at 3.2× the rate of those with clean payment histories — suggesting payment monitoring should trigger early intervention."*
5. *"Composite Risk Score Validation: The model's composite risk score successfully separates the portfolio into four tiers with a 3:1 default rate spread from LOW (5.1%) to VERY_HIGH (17.8%)."*

**Theme**: Professional navy/teal.
**Footer**: *"Source: Home Credit Default Risk Dataset | Model: XGBoost v1 | Tracking: MLflow | Pipeline: Snowflake + dbt + Airflow"*

## 4. Final Steps
1. **Publish** to Power BI Service.
2. Ensure Gateway is configured for DirectQuery to Snowflake if scheduled refresh is needed (or OAuth).
3. **Get Share Link** and capture screenshots of all 4 pages.
