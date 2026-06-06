# Power BI — Star Schema Design

## Overview

The CanCredit Power BI model follows a **star schema** with one central fact table
and lightweight dimension tables derived from the Snowflake mart layer.

---

## Schema Diagram

```
                        ┌─────────────────────┐
                        │   Dim_RiskSegment   │
                        │─────────────────────│
                        │ credit_risk_segment │◄──┐
                        │ risk_order          │   │
                        └─────────────────────┘   │
                                                   │
┌─────────────────────┐   ┌──────────────────────────────────────────────┐
│    Dim_LoanType     │   │          MART_CREDIT_APPLICATION_FACT         │
│─────────────────────│   │──────────────────────────────────────────────│
│ loan_type (PK)      │◄──│ applicant_id (PK)                            │
└─────────────────────┘   │ default_flag                                 │
                          │ loan_type (FK → Dim_LoanType)               │
┌─────────────────────┐   │ credit_risk_segment (FK → Dim_RiskSegment)  │
│   Dim_Education     │   │ education_level (FK → Dim_Education)         │
│─────────────────────│   │ income_type (FK → Dim_IncomeType)            │
│ education_level (PK)│◄──│ gender                                       │
└─────────────────────┘   │ age_years                                    │
                          │ years_employed                               │
┌─────────────────────┐   │ loan_amount                                  │
│   Dim_IncomeType    │   │ annual_income                                │
│─────────────────────│   │ credit_to_income_ratio                       │
│ income_type (PK)    │◄──│ annuity_to_income_ratio                      │
└─────────────────────┘   │ ext_source_1 / 2 / 3                        │
                          │ bureau_active_credits                        │
                          │ bureau_total_debt                            │
                          │ bureau_total_overdue                         │
                          │ bureau_delinquency_rate                      │
                          │ bureau_worst_delinquency                     │
                          │ bureau_num_records                           │
                          │ inst_late_rate                               │
                          │ inst_max_days_late                           │
                          │ inst_avg_payment_ratio                       │
                          │ inst_total_underpaid                         │
                          │ cc_avg_utilization                           │
                          │ cc_max_utilization                           │
                          │ cc_months_overdue                            │
                          │ prev_num_applications                        │
                          │ prev_refusal_rate                            │
                          │ prev_approved                                │
                          │ composite_risk_score                         │
                          │ dbt_updated_at                               │
                          └──────────────────────────────────────────────┘
```

---

## Dimension Tables

### Dim_RiskSegment
Created as a calculated table in Power BI (not from Snowflake):
```dax
Dim_RiskSegment =
DATATABLE(
    "credit_risk_segment", STRING,
    "risk_order", INTEGER,
    "description", STRING,
    "dti_threshold", STRING,
    {
        {"LOW",       1, "Credit-to-income ≤ 1.5", "≤ 1.5×"},
        {"MEDIUM",    2, "Credit-to-income 1.5–3.0", "1.5–3.0×"},
        {"HIGH",      3, "Credit-to-income 3.0–5.0", "3.0–5.0×"},
        {"VERY_HIGH", 4, "Credit-to-income > 5.0", "> 5.0×"}
    }
)
```

Relationship: `MART_CREDIT_APPLICATION_FACT[CREDIT_RISK_SEGMENT]` → `Dim_RiskSegment[credit_risk_segment]` (Many-to-One)

### Dim_LoanType
```dax
Dim_LoanType =
DATATABLE(
    "loan_type", STRING,
    "loan_type_short", STRING,
    {
        {"Cash loans",      "Cash"},
        {"Revolving loans", "Revolving"}
    }
)
```

Relationship: `MART_CREDIT_APPLICATION_FACT[LOAN_TYPE]` → `Dim_LoanType[loan_type]` (Many-to-One)

---

## Relationship Settings

| From Table | From Column | To Table | To Column | Cardinality | Cross-filter |
|---|---|---|---|---|---|
| MART_CREDIT_APPLICATION_FACT | CREDIT_RISK_SEGMENT | Dim_RiskSegment | credit_risk_segment | Many-to-One | Single |
| MART_CREDIT_APPLICATION_FACT | LOAN_TYPE | Dim_LoanType | loan_type | Many-to-One | Single |

> All relationships use **Single** cross-filter direction to avoid circular dependency issues with bidirectional filters on large DirectQuery datasets.

---

## Grain

**Fact table grain**: One row per loan applicant (`applicant_id`)
- 307,511 rows (application_train.csv)
- DirectQuery — no data is imported into Power BI Desktop

---

## Why Not a Full Dimension Model?

Many columns (education_level, income_type, housing_type, etc.) are kept **directly in the fact table** rather than spun into separate dimension tables. This is intentional:

1. **DirectQuery performance**: Joining back to Snowflake dimension tables on every visual render adds latency. With 300K rows and ~50ms Snowflake query time, keeping dimensions in the fact table reduces cross-table joins.
2. **Low cardinality**: Most "dimension" columns have fewer than 10 distinct values — there's no storage benefit to normalizing them.
3. **dbt already handles this**: The star schema normalization is done in `mart_portfolio_summary.sql` for aggregated Power BI queries — the summary table is used for treemaps and heatmaps that group heavily.

---

## MART_PORTFOLIO_SUMMARY Usage

For visuals that aggregate heavily (treemaps, heatmaps with education × risk segment), use the pre-aggregated `MART_PORTFOLIO_SUMMARY` table to avoid DirectQuery timeout on GROUP BY queries:

```
MART_PORTFOLIO_SUMMARY columns:
  loan_type, education_level, credit_risk_segment,
  gender, income_type,
  total_applications, total_defaults, default_rate_pct,
  avg_loan_amount, avg_annual_income, avg_dti, avg_risk_score
```

Import mode is acceptable for this table — it's small (~200 rows) and pre-aggregated by dbt.
