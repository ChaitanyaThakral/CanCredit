-- =============================================================================
-- Snowflake Data Quality Alert: cancredit_dq_alert
-- Schedule: 08:00 ET, Mon-Fri
-- Purpose: Detect bad data in mart_credit_application_fact and send an email
--          alert before business users hit the Power BI dashboard.
--
-- Prerequisites:
--   1. Email integration must be enabled for your Snowflake account.
--   2. CANCREDIT_WH must be running (or set AUTO_RESUME = TRUE).
--   3. Run: ALTER ALERT cancredit_dq_alert RESUME;  after creation.
-- =============================================================================

CREATE OR REPLACE ALERT cancredit_dq_alert
    WAREHOUSE = CANCREDIT_WH
    SCHEDULE  = 'USING CRON 0 8 * * 1-5 America/Toronto'
    IF (EXISTS (
        SELECT 1
        FROM CANCREDIT_DB.MARTS.MART_CREDIT_APPLICATION_FACT
        WHERE credit_to_income_ratio   < 0
           OR bureau_delinquency_rate  > 1
           OR inst_late_rate           > 1
           OR composite_risk_score     > 1
           OR composite_risk_score     < 0
           OR default_flag NOT IN (0, 1)
           OR credit_risk_segment NOT IN ('LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH')
        LIMIT 1
    ))
    THEN CALL SYSTEM$SEND_EMAIL(
        'admin@cancredit.local',
        'CanCredit DQ Alert 🚨',
        'Data quality check FAILED on MART_CREDIT_APPLICATION_FACT. '
        || 'One or more rows violate domain constraints. '
        || 'Check: credit_to_income_ratio >= 0, delinquency rates in [0,1], '
        || 'composite_risk_score in [0,1], default_flag in {0,1}.'
    );

-- Resume the alert so it runs on schedule:
ALTER ALERT cancredit_dq_alert RESUME;

-- =============================================================================
-- Verify alert status
-- =============================================================================
SHOW ALERTS LIKE 'cancredit_dq_alert';
