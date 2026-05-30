# Data Dictionary

## APPLICATION_TRAIN

This table contains the main training dataset with information about each loan application.

| Column Name | Type | Description |
|---|---|---|
| `SK_ID_CURR` | INT | ID of loan in our sample |
| `TARGET` | INT | Target variable (1 - client with payment difficulties: he/she had late payment more than X days on at least one of the first Y installments of the loan in our sample, 0 - all other cases) |
| `NAME_CONTRACT_TYPE` | VARCHAR | Identification if loan is cash or revolving |
| `CODE_GENDER` | VARCHAR | Gender of the client |
| `FLAG_OWN_CAR` | VARCHAR | Flag if the client owns a car |
| `FLAG_OWN_REALTY` | VARCHAR | Flag if client owns a house or flat |
| `CNT_CHILDREN` | INT | Number of children the client has |
| `AMT_INCOME_TOTAL` | FLOAT | Income of the client |
| `AMT_CREDIT` | FLOAT | Credit amount of the loan |
| `AMT_ANNUITY` | FLOAT | Loan annuity |
| `AMT_GOODS_PRICE` | FLOAT | For consumer loans it is the price of the goods for which the loan is given |
| `NAME_TYPE_SUITE` | VARCHAR | Who was accompanying client when he was applying for the loan |
| `NAME_INCOME_TYPE` | VARCHAR | Clients income type (businessman, working, maternity leave,...) |
| `NAME_EDUCATION_TYPE` | VARCHAR | Level of highest education the client achieved |
| `NAME_FAMILY_STATUS` | VARCHAR | Family status of the client |
| `NAME_HOUSING_TYPE` | VARCHAR | What is the housing situation of the client (renting, living with parents, ...) |
| `REGION_POPULATION_RELATIVE` | FLOAT | Normalized population of region where client lives |
| `DAYS_BIRTH` | INT | Client's age in days at the time of application |
| `DAYS_EMPLOYED` | INT | How many days before the application the person started current employment |
| `DAYS_REGISTRATION` | FLOAT | How many days before the application did client change his registration |
| `DAYS_ID_PUBLISH` | INT | How many days before the application did client change the identity document with which he applied for the loan |
| `OWN_CAR_AGE` | FLOAT | Age of client's car |
| `FLAG_MOBIL` | INT | Did client provide mobile phone (1=YES, 0=NO) |
| `FLAG_EMP_PHONE` | INT | Did client provide work phone (1=YES, 0=NO) |
| `EXT_SOURCE_1` | FLOAT | Normalized score from external data source |
| `EXT_SOURCE_2` | FLOAT | Normalized score from external data source |
| `EXT_SOURCE_3` | FLOAT | Normalized score from external data source |
