# Power BI — DAX Measures Reference

All measures are added in the **MART_CREDIT_APPLICATION_FACT** table unless noted.
Create via: **Report view** → **Table Tools** → **New Measure**

---

## Core KPI Measures

### Default Rate %
```dax
Default Rate % =
DIVIDE(
    COUNTROWS(FILTER('MART_CREDIT_APPLICATION_FACT', 'MART_CREDIT_APPLICATION_FACT'[DEFAULT_FLAG] = 1)),
    COUNTROWS('MART_CREDIT_APPLICATION_FACT'),
    0
) * 100
```

### Total Defaults
```dax
Total Defaults =
CALCULATE(
    COUNTROWS('MART_CREDIT_APPLICATION_FACT'),
    'MART_CREDIT_APPLICATION_FACT'[DEFAULT_FLAG] = 1
)
```

### Total Applications
```dax
Total Applications = COUNTROWS('MART_CREDIT_APPLICATION_FACT')
```

### Avg Loan Amount
```dax
Avg Loan Amount =
AVERAGE('MART_CREDIT_APPLICATION_FACT'[LOAN_AMOUNT])
```

### Avg Annual Income
```dax
Avg Annual Income =
AVERAGE('MART_CREDIT_APPLICATION_FACT'[ANNUAL_INCOME])
```

### Avg Credit-to-Income Ratio (DTI)
```dax
Avg DTI =
AVERAGE('MART_CREDIT_APPLICATION_FACT'[CREDIT_TO_INCOME_RATIO])
```

---

## Risk Tier Measures

### High Risk Count
```dax
High Risk Count =
CALCULATE(
    COUNTROWS('MART_CREDIT_APPLICATION_FACT'),
    'MART_CREDIT_APPLICATION_FACT'[CREDIT_RISK_SEGMENT] IN {"HIGH", "VERY_HIGH"}
)
```

### High Risk % of Portfolio
```dax
High Risk % =
DIVIDE([High Risk Count], [Total Applications], 0) * 100
```

### Very High vs Low Default Ratio
Key resume talking point: "VERY_HIGH segment defaults at 3.5× the LOW segment rate"
```dax
Very High vs Low Default Ratio =
VAR very_high_rate =
    CALCULATE(
        [Default Rate %],
        'MART_CREDIT_APPLICATION_FACT'[CREDIT_RISK_SEGMENT] = "VERY_HIGH"
    )
VAR low_rate =
    CALCULATE(
        [Default Rate %],
        'MART_CREDIT_APPLICATION_FACT'[CREDIT_RISK_SEGMENT] = "LOW"
    )
RETURN
DIVIDE(very_high_rate, low_rate, 0)
```

Display format: `0.0"×"` → shows as "3.5×"

### Default Rate by Segment (used in matrix conditional formatting)
```dax
Default Rate by Segment =
CALCULATE(
    [Default Rate %],
    ALLEXCEPT(
        'MART_CREDIT_APPLICATION_FACT',
        'MART_CREDIT_APPLICATION_FACT'[CREDIT_RISK_SEGMENT]
    )
)
```

---

## Payment Behaviour Measures

### Avg Late Payment Rate %
Resume talking point: "25% late-payment rate for defaulters vs. 8% baseline"
```dax
Avg Inst Late Rate % =
AVERAGE('MART_CREDIT_APPLICATION_FACT'[INST_LATE_RATE]) * 100
```

### Defaulter Late Payment Rate %
```dax
Defaulter Late Rate % =
CALCULATE(
    AVERAGE('MART_CREDIT_APPLICATION_FACT'[INST_LATE_RATE]) * 100,
    'MART_CREDIT_APPLICATION_FACT'[DEFAULT_FLAG] = 1
)
```

### Non-Defaulter Late Payment Rate %
```dax
Non-Defaulter Late Rate % =
CALCULATE(
    AVERAGE('MART_CREDIT_APPLICATION_FACT'[INST_LATE_RATE]) * 100,
    'MART_CREDIT_APPLICATION_FACT'[DEFAULT_FLAG] = 0
)
```

### Late Payment Lift (Defaulters vs Non-Defaulters)
```dax
Late Payment Lift =
DIVIDE([Defaulter Late Rate %], [Non-Defaulter Late Rate %], 0)
```

Expected result: ~3.1× (25% ÷ 8%)

---

## Bureau Risk Measures

### Avg Bureau Delinquency Rate %
```dax
Avg Bureau Delinquency % =
AVERAGE('MART_CREDIT_APPLICATION_FACT'[BUREAU_DELINQUENCY_RATE]) * 100
```

### Avg Bureau Total Overdue
```dax
Avg Bureau Overdue =
AVERAGE('MART_CREDIT_APPLICATION_FACT'[BUREAU_TOTAL_OVERDUE])
```

### % Applicants with Bureau Record
```dax
% With Bureau Record =
DIVIDE(
    CALCULATE(
        COUNTROWS('MART_CREDIT_APPLICATION_FACT'),
        'MART_CREDIT_APPLICATION_FACT'[BUREAU_NUM_RECORDS] > 0
    ),
    [Total Applications],
    0
) * 100
```

---

## Composite Risk Score Measures

### Avg Risk Score
```dax
Avg Risk Score =
AVERAGE('MART_CREDIT_APPLICATION_FACT'[COMPOSITE_RISK_SCORE])
```

### Risk Score P90 (high-risk threshold)
```dax
Risk Score P90 =
PERCENTILEX.INC(
    'MART_CREDIT_APPLICATION_FACT',
    'MART_CREDIT_APPLICATION_FACT'[COMPOSITE_RISK_SCORE],
    0.90
)
```

---

## Decision Funnel Measure
Used on Page 4 funnel chart:
```dax
Decision Funnel =
SWITCH(
    SELECTEDVALUE('Dim_RiskSegment'[credit_risk_segment]),
    "LOW",       CALCULATE([Total Applications], 'MART_CREDIT_APPLICATION_FACT'[CREDIT_RISK_SEGMENT] = "LOW"),
    "MEDIUM",    CALCULATE([Total Applications], 'MART_CREDIT_APPLICATION_FACT'[CREDIT_RISK_SEGMENT] = "MEDIUM"),
    "HIGH",      CALCULATE([Total Applications], 'MART_CREDIT_APPLICATION_FACT'[CREDIT_RISK_SEGMENT] = "HIGH"),
    "VERY_HIGH", CALCULATE([Total Applications], 'MART_CREDIT_APPLICATION_FACT'[CREDIT_RISK_SEGMENT] = "VERY_HIGH"),
    BLANK()
)
```

---

## Formatting Reference

| Measure | Format String | Example |
|---|---|---|
| Default Rate % | `0.00"%"` | 8.07% |
| Very High vs Low Ratio | `0.0"×"` | 3.5× |
| Avg Loan Amount | `"$"#,##0` | $597,383 |
| Avg Annual Income | `"$"#,##0` | $168,798 |
| Avg Risk Score | `0.000` | 0.142 |
| Late Payment Lift | `0.0"×"` | 3.1× |
| Total Applications | `#,##0` | 307,511 |

---

## Age Band Calculated Column
Add in **MART_CREDIT_APPLICATION_FACT** → **New Column**:
```dax
Age Band =
SWITCH(
    TRUE(),
    'MART_CREDIT_APPLICATION_FACT'[AGE_YEARS] < 30, "Under 30",
    'MART_CREDIT_APPLICATION_FACT'[AGE_YEARS] < 45, "30–44",
    'MART_CREDIT_APPLICATION_FACT'[AGE_YEARS] < 60, "45–59",
    "60+"
)
```

## Income Bracket Calculated Column
```dax
Income Bracket =
SWITCH(
    TRUE(),
    'MART_CREDIT_APPLICATION_FACT'[ANNUAL_INCOME] < 90000,  "1_Low (<$90K)",
    'MART_CREDIT_APPLICATION_FACT'[ANNUAL_INCOME] < 180000, "2_Mid ($90–$180K)",
    'MART_CREDIT_APPLICATION_FACT'[ANNUAL_INCOME] < 360000, "3_High ($180–$360K)",
    "4_Very High ($360K+)"
)
```
