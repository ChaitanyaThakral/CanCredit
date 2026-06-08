# CanCredit — Data Dictionary

> **Audience**: Data Analysts, Credit Risk Analysts, Business Stakeholders
> Documents all source tables (Home Credit + Bank of Canada) and key derived columns in the mart layer.

---

## Source Tables (RAW Schema)

### APPLICATION_TRAIN
**58M-row primary table** | 307,511 rows | 122 columns

The core training dataset with one row per loan application. `TARGET` is the label.

| Column | Type | Description | Notes |
|---|---|---|---|
| `SK_ID_CURR` | INT | Unique loan application ID | Primary key |
| `TARGET` | INT | Default label (1 = defaulted, 0 = repaid) | 8.07% default rate |
| `NAME_CONTRACT_TYPE` | VARCHAR | Cash loans vs Revolving loans | 2 values |
| `CODE_GENDER` | VARCHAR | Applicant gender (M/F/XNA) | XNA = not disclosed |
| `FLAG_OWN_CAR` | VARCHAR | Owns a car (Y/N) | |
| `FLAG_OWN_REALTY` | VARCHAR | Owns property (Y/N) | |
| `CNT_CHILDREN` | INT | Number of dependent children | |
| `AMT_INCOME_TOTAL` | FLOAT | Annual income (local currency) | Never zero in clean data |
| `AMT_CREDIT` | FLOAT | Loan amount requested | |
| `AMT_ANNUITY` | FLOAT | Monthly loan payment amount | |
| `AMT_GOODS_PRICE` | FLOAT | Price of goods financed (consumer loans) | NULL for cash loans |
| `NAME_INCOME_TYPE` | VARCHAR | Income source (Working, Pensioner, Commercial associate…) | 8 categories |
| `NAME_EDUCATION_TYPE` | VARCHAR | Highest education level | 5 categories |
| `NAME_FAMILY_STATUS` | VARCHAR | Marital status | 5 categories |
| `NAME_HOUSING_TYPE` | VARCHAR | Housing situation (renting, owned, parents…) | 6 categories |
| `REGION_POPULATION_RELATIVE` | FLOAT | Normalised regional population | 0–0.07 range |
| `DAYS_BIRTH` | INT | Age in days (negative: days before application) | Divide by -365.25 for years |
| `DAYS_EMPLOYED` | INT | Days employed (negative = before application) | **365243 = unemployed sentinel** |
| `DAYS_REGISTRATION` | FLOAT | Days since address registration change | Negative |
| `DAYS_ID_PUBLISH` | INT | Days since ID document last changed | Negative |
| `OWN_CAR_AGE` | FLOAT | Age of car owned (years) | NULL if no car |
| `FLAG_WORK_PHONE` | INT | Has work phone (1/0) | |
| `FLAG_EMAIL` | INT | Has email address (1/0) | |
| `EXT_SOURCE_1` | FLOAT | Normalised external credit score 1 | 56% NULL rate |
| `EXT_SOURCE_2` | FLOAT | Normalised external credit score 2 | Strongest predictor |
| `EXT_SOURCE_3` | FLOAT | Normalised external credit score 3 | 25% NULL rate |
| `OCCUPATION_TYPE` | VARCHAR | Job category | 31% NULL |
| `CNT_FAM_MEMBERS` | FLOAT | Household size | |
| `REGION_RATING_CLIENT` | INT | Region risk rating (1/2/3, 3=highest risk) | |
| `DAYS_DECISION` | INT | Days from application to decision | Negative |

**Key derived ratios** (calculated in `stg_application_train.sql`):
- `credit_to_income_ratio` = `AMT_CREDIT / AMT_INCOME_TOTAL`
- `annuity_to_income_ratio` = `AMT_ANNUITY / AMT_INCOME_TOTAL`
- `age_years` = `FLOOR(ABS(DAYS_BIRTH) / 365.25)`
- `years_employed` = `NULL if DAYS_EMPLOYED = 365243 else FLOOR(ABS(DAYS_EMPLOYED) / 365.25)`

---

### BUREAU
**1,716,428 rows** | Credit bureau records from other institutions

One row per credit product per applicant. Applicants may have 0–30+ bureau records.

| Column | Type | Description |
|---|---|---|
| `SK_ID_CURR` | INT | FK → APPLICATION_TRAIN |
| `SK_ID_BUREAU` | INT | Bureau record ID (PK) |
| `CREDIT_ACTIVE` | VARCHAR | Active / Closed / Sold / Bad debt |
| `CREDIT_CURRENCY` | VARCHAR | Currency of credit |
| `DAYS_CREDIT` | INT | Days before application the credit was reported |
| `DAYS_CREDIT_ENDDATE` | INT | Expected end date of credit (days) |
| `AMT_CREDIT_SUM` | FLOAT | Current credit amount |
| `AMT_CREDIT_SUM_DEBT` | FLOAT | Current debt on credit |
| `AMT_CREDIT_SUM_OVERDUE` | FLOAT | Amount overdue |
| `AMT_CREDIT_SUM_LIMIT` | FLOAT | Credit limit |
| `CREDIT_TYPE` | VARCHAR | Consumer credit / Credit card / Mortgage / Auto loan…  |

---

### BUREAU_BALANCE
**27,299,925 rows** | Monthly bureau balance history per bureau record

| Column | Type | Description |
|---|---|---|
| `SK_ID_BUREAU` | INT | FK → BUREAU |
| `MONTHS_BALANCE` | INT | Month (0=current, -1=last month…) |
| `STATUS` | VARCHAR | Payment status: 0=ok, 1-5=DPD bucket, C=closed, X=unknown |

**Key insight**: `STATUS IN ('1','2','3','4','5')` indicates delinquency.
`bureau_worst_delinquency` = MAX(STATUS::INT) captures the worst-ever DPD bucket.

---

### INSTALLMENTS_PAYMENTS
**13,605,401 rows** | Payment history for previous loans

| Column | Type | Description |
|---|---|---|
| `SK_ID_PREV` | INT | Previous loan ID |
| `SK_ID_CURR` | INT | FK → APPLICATION_TRAIN |
| `NUM_INSTALMENT_VERSION` | FLOAT | Version of instalment schedule |
| `NUM_INSTALMENT_NUMBER` | FLOAT | Instalment number in schedule |
| `DAYS_INSTALMENT` | FLOAT | Expected payment day |
| `DAYS_ENTRY_PAYMENT` | FLOAT | Actual payment day |
| `AMT_INSTALMENT` | FLOAT | Amount due |
| `AMT_PAYMENT` | FLOAT | Amount actually paid |

**Key derived metrics**:
- `days_late` = `MAX(DAYS_ENTRY_PAYMENT - DAYS_INSTALMENT, 0)`
- `is_late` = `DAYS_ENTRY_PAYMENT > DAYS_INSTALMENT`
- `payment_ratio` = `AMT_PAYMENT / AMT_INSTALMENT` (>1 = overpayment)

---

### CREDIT_CARD_BALANCE
**3,840,312 rows** | Monthly credit card balance snapshots

| Column | Type | Description |
|---|---|---|
| `SK_ID_PREV` | INT | Previous loan ID |
| `SK_ID_CURR` | INT | FK → APPLICATION_TRAIN |
| `MONTHS_BALANCE` | INT | Month offset from application |
| `AMT_BALANCE` | FLOAT | Outstanding balance |
| `AMT_CREDIT_LIMIT_ACTUAL` | FLOAT | Credit limit this month |
| `AMT_DRAWINGS_CURRENT` | FLOAT | Drawings (withdrawals) this month |
| `AMT_PAYMENT_CURRENT` | FLOAT | Payment made this month |
| `SK_DPD` | INT | Days past due |
| `SK_DPD_DEF` | INT | Days past due (tolerant definition) |

**Key derived**: `cc_avg_utilization` = `AVG(AMT_BALANCE / AMT_CREDIT_LIMIT_ACTUAL)`

---

### PREVIOUS_APPLICATION
**1,670,214 rows** | Prior loan applications at Home Credit

| Column | Type | Description |
|---|---|---|
| `SK_ID_PREV` | INT | Previous application ID (PK) |
| `SK_ID_CURR` | INT | FK → APPLICATION_TRAIN |
| `NAME_CONTRACT_TYPE` | VARCHAR | Cash / Consumer / Revolving |
| `NAME_CONTRACT_STATUS` | VARCHAR | **Approved / Refused / Canceled / Unused offer** |
| `AMT_CREDIT` | FLOAT | Credit amount applied for |
| `AMT_ANNUITY` | FLOAT | Annuity requested |
| `DAYS_DECISION` | INT | Days before current application the decision was made |

**Key derived**: `prev_refusal_rate` = `COUNT(Refused) / COUNT(*)` — high refusal rate is a strong default predictor.

---

### POS_CASH_BALANCE
**10,001,358 rows** | Monthly POS and cash loan status

| Column | Type | Description |
|---|---|---|
| `SK_ID_PREV` | INT | Previous loan ID |
| `SK_ID_CURR` | INT | FK → APPLICATION_TRAIN |
| `MONTHS_BALANCE` | INT | Month offset |
| `CNT_INSTALMENT` | FLOAT | Contractual instalments |
| `CNT_INSTALMENT_FUTURE` | FLOAT | Remaining instalments |
| `NAME_CONTRACT_STATUS` | VARCHAR | Active / Completed / Returned to the store… |
| `SK_DPD` | INT | Days past due |
| `SK_DPD_DEF` | INT | Days past due (tolerant) |

---

### BOC_MACRO
**~2,800 rows** | Bank of Canada macro indicators (2015–present)

| Column | Type | Description |
|---|---|---|
| `DATE` | DATE | Observation date (business days) |
| `OVERNIGHT_RATE` | FLOAT | BoC overnight lending rate target (%) |
| `BOND_YIELD_2YR` | FLOAT | 2-year Government of Canada bond yield (%) |
| `BOND_YIELD_10YR` | FLOAT | 10-year Government of Canada bond yield (%) |
| `FX_CAD_USD` | FLOAT | CAD/USD exchange rate |
| `CPI_ALL` | FLOAT | CPI total change YoY (%) |

**Data source**: Bank of Canada Valet API — https://www.bankofcanada.ca/valet/observations/
**Update frequency**: Daily (weekdays), fetched by `boc_macro_daily` Airflow DAG

---

## Mart Layer (MARTS Schema)

### MART_CREDIT_APPLICATION_FACT
**307,511 rows** | One row per applicant — central Power BI and ML table

| Column | Type | Description |
|---|---|---|
| `applicant_id` | INT | Unique applicant ID (PK) |
| `default_flag` | INT | 1 = defaulted, 0 = repaid |
| `loan_type` | VARCHAR | Cash loans / Revolving loans |
| `credit_risk_segment` | VARCHAR | **LOW / MEDIUM / HIGH / VERY_HIGH** (based on credit-to-income ratio) |
| `composite_risk_score` | FLOAT | Weighted risk score 0–1 (see formula below) |
| `bureau_active_credits` | INT | Number of active credit bureau records |
| `bureau_delinquency_rate` | FLOAT | Proportion of bureau months with delinquency |
| `bureau_worst_delinquency` | INT | Worst DPD bucket ever recorded (0–5) |
| `inst_late_rate` | FLOAT | Proportion of late installment payments |
| `inst_max_days_late` | FLOAT | Maximum days late on any single payment |
| `inst_avg_payment_ratio` | FLOAT | Avg payment / amount due (>1 = overpayment habit) |
| `cc_avg_utilization` | FLOAT | Avg credit card utilization (balance/limit) |
| `cc_months_overdue` | INT | Total months with credit card DPD > 0 |
| `prev_refusal_rate` | FLOAT | Prior loan refusal rate (0–1) |
| `composite_risk_score` | FLOAT | `0.30×bureau_delinq + 0.25×inst_late + 0.20×dti/10 + 0.15×cc_util/3 + 0.10×prev_refusal` |

**Risk segment thresholds**:
- `LOW`: credit_to_income_ratio ≤ 1.5
- `MEDIUM`: 1.5 < ratio ≤ 3.0
- `HIGH`: 3.0 < ratio ≤ 5.0
- `VERY_HIGH`: ratio > 5.0

---

### ML_FEATURES.ML_FEATURES_TRAINING
**~284,000 rows** | Purpose-built feature store for XGBoost training (labelled rows only)

18 features selected for: null rate < 20%, predictive power from EDA.
See `notebooks/01_credit_risk_eda_and_model.ipynb` for feature selection rationale.

| Feature | Type | Range | Importance |
|---|---|---|---|
| `ext_source_2` | FLOAT | 0–1 | ⭐⭐⭐⭐⭐ (strongest) |
| `ext_source_3` | FLOAT | 0–1 | ⭐⭐⭐⭐ |
| `ext_source_1` | FLOAT | 0–1 | ⭐⭐⭐ |
| `bureau_delinquency_rate` | FLOAT | 0–1 | ⭐⭐⭐⭐ |
| `inst_late_rate` | FLOAT | 0–1 | ⭐⭐⭐⭐ |
| `inst_avg_payment_ratio` | FLOAT | ≥0 | ⭐⭐⭐ |
| `credit_to_income_ratio` | FLOAT | ≥0 | ⭐⭐⭐ |
| `composite_risk_score` | FLOAT | 0–1 | ⭐⭐⭐ |
| `inst_max_days_late` | FLOAT | ≥0 | ⭐⭐ |
| `prev_refusal_rate` | FLOAT | 0–1 | ⭐⭐ |
| `age_years` | FLOAT | 18–70 | ⭐⭐ |
| `annuity_to_income_ratio` | FLOAT | ≥0 | ⭐⭐ |
| `bureau_worst_delinquency` | FLOAT | 0–5 | ⭐⭐ |
| `bureau_total_overdue` | FLOAT | ≥0 | ⭐ |
| `cc_avg_utilization` | FLOAT | 0–3 | ⭐ |
| `cc_months_overdue` | FLOAT | ≥0 | ⭐ |
| `prev_num_applications` | FLOAT | ≥0 | ⭐ |
| `years_employed` | FLOAT | ≥0 | ⭐ |
