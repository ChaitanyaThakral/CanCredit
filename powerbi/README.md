# Power BI Dashboard — Setup Guide

> **CanCredit Credit Risk Dashboard** — 4-page Power BI report over 307,511 loan applications,
> using DirectQuery to Snowflake for live data. This is the primary Data Analyst/BA deliverable.

---

## Prerequisites

| Requirement | Version |
|---|---|
| Power BI Desktop | June 2024+ |
| Snowflake ODBC Driver | 2.25+ |
| Snowflake account | CANCREDIT_DB with MARTS schema populated |

---

## 1. Connect Power BI to Snowflake

1. Open Power BI Desktop → **Get Data** → **Snowflake**
2. Enter connection details:
   - **Server**: `<your-account>.snowflakecomputing.com`
   - **Warehouse**: `CANCREDIT_WH`
   - **Database**: `CANCREDIT_DB`
   - **Schema**: `MARTS`
3. Choose **DirectQuery** (not Import) — this ensures the dashboard reflects the latest dbt run without manual refresh
4. Authenticate with your Snowflake username + password

---

## 2. Import Tables

Select these tables from the MARTS schema:

| Table | Purpose |
|---|---|
| `MART_CREDIT_APPLICATION_FACT` | Main fact table — 307K applicants |
| `MART_PORTFOLIO_SUMMARY` | Pre-aggregated metrics (optional, for heavy visuals) |

> **Note**: `ML_FEATURES.ML_FEATURES_TRAINING` can optionally be added for the model score page.

---

## 3. Star Schema Setup in Power BI

After importing, create dimension tables using **Transform Data** → **New Query**:

### Dim_LoanType
```powerquery
= Table.SelectColumns(MART_CREDIT_APPLICATION_FACT, {"loan_type"})
  |> Table.Distinct()
  |> Table.AddIndexColumn("loan_type_key", 1, 1, Int64.Type)
```

### Dim_Education
```powerquery
= Table.SelectColumns(MART_CREDIT_APPLICATION_FACT, {"education_level"})
  |> Table.Distinct()
  |> Table.AddIndexColumn("education_key", 1, 1, Int64.Type)
```

### Dim_RiskSegment
```powerquery
= Table.FromRows(
    {{"LOW", 1}, {"MEDIUM", 2}, {"HIGH", 3}, {"VERY_HIGH", 4}},
    {"credit_risk_segment", "risk_order"}
)
```

See `star_schema.md` for full relationship diagram.

---

## 4. Dashboard Pages

### Page 1 — Executive Overview
**Audience**: Credit Risk VP, Portfolio Manager
**Headline KPIs** (card visuals):
- Default Rate: `[Default Rate %]`
- Total Applications: `COUNT(applicant_id)`
- Avg Loan Amount: `[Avg Loan Amount]`
- High-Risk Applications: `[High Risk Count]`

**Main visual**: Default rate by risk segment (clustered bar chart)
- X-axis: `credit_risk_segment` (sorted by risk_order)
- Y-axis: `[Default Rate %]`
- Color: conditional formatting (green → red gradient)

**Secondary visual**: Loan volume over age band (area chart)
- X-axis: age bucket (derived column: `IF(age_years < 30, "Under 30", IF(age_years < 45, "30–44", IF(age_years < 60, "45–59", "60+"))`)
- Y-axis: `COUNT(applicant_id)`

**Slicer panel**: loan_type, gender, income_type

---

### Page 2 — Default Risk Drivers
**Audience**: Risk Analyst, Credit Underwriter
**Purpose**: Show the 3.5× default rate gap — the key portfolio insight

**Main visual**: Scatter plot
- X-axis: `composite_risk_score`
- Y-axis: `bureau_delinquency_rate`
- Size: `loan_amount`
- Color: `default_flag` (0=blue, 1=red)

**Visual 2**: Matrix table
- Rows: `credit_risk_segment`
- Columns: `education_level`
- Values: `[Default Rate %]`
- Conditional formatting: data bars

**Visual 3**: 100% stacked bar — late payment rate by segment
- X-axis: `credit_risk_segment`
- Y-axis: `inst_late_rate` (average)
- Reference line at 0.08 (8% portfolio baseline)

**KPI card**: "VERY_HIGH segment defaults at **3.5×** the LOW segment rate"
- Value: `[Very High vs Low Default Ratio]`

---

### Page 3 — Bureau & Payment Behaviour
**Audience**: Data Analyst, Underwriting Team
**Purpose**: Drill-down on credit bureau delinquency and installment discipline

**Visual 1**: Box-and-whisker (or violin approximation using P5/P25/P75/P95)
- Bureau delinquency rate by default flag
- Use custom DAX quartile measures

**Visual 2**: Waterfall chart
- Components of composite_risk_score by risk segment
- Shows weight of each factor: bureau_delinquency_rate (30%), inst_late_rate (25%), etc.

**Visual 3**: KPI gauges
- `[Avg Inst Late Rate]` vs 8% target
- `[Avg Bureau Delinquency Rate]` vs 10% target

**Table**: Top 20 highest-risk applicants (anonymised — applicant_id only)
- Columns: applicant_id, credit_risk_segment, composite_risk_score, default_flag

---

### Page 4 — Portfolio Segmentation
**Audience**: Product Manager, Credit Policy Team
**Purpose**: Segment portfolio by income, loan type, geography for policy recommendations

**Visual 1**: Treemap
- Group by: income_type → education_level
- Size: `COUNT(applicant_id)`
- Color: `[Default Rate %]`

**Visual 2**: Heatmap (matrix with conditional formatting)
- Rows: age band
- Columns: income bracket
- Values: `[Default Rate %]`

**Visual 3**: Funnel chart
- Applications → Approved (LOW risk) → Conditional (MEDIUM) → Review (HIGH) → Declined (VERY_HIGH)
- Uses `[Decision Funnel]` measure

**Insight text box**: "Working-class applicants under 30 with credit-to-income > 5 default at 28% — 3.5× the portfolio average"

---

## 5. Publish & Share

1. **Power BI Service**: File → Publish to Power BI → Select your workspace
2. **Schedule refresh**: Not needed with DirectQuery
3. **Row-level security**: In Power BI Service → Manage roles → Create `ANALYST` role with `[income_type] = USERNAME()` filter
4. **Export embed URL** for portfolio: Copy from Power BI Service → File → Embed Report → Website or portal

---

## 6. Interview Talking Points

> "I built a 4-page Power BI dashboard connected via DirectQuery to Snowflake, so the credit team always sees live data from the daily Airflow pipeline run. The key finding was that the VERY_HIGH risk segment — defined by credit-to-income ratio above 5 — defaults at 3.5 times the rate of the LOW segment. That drove 5 credit policy recommendations including tightening the DTI threshold from 5× to 4× income for new applicants."
