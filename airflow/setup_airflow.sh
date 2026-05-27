#!/usr/bin/env bash
# =============================================================================
# Airflow setup script — run once on a fresh Linux/Mac environment.
# On Windows, use the Docker Compose approach instead (see docker-compose.yml).
# =============================================================================
set -euo pipefail

export AIRFLOW_HOME="${AIRFLOW_HOME:-$HOME/airflow}"
export AIRFLOW__CORE__EXECUTOR=LocalExecutor
export AIRFLOW__CORE__LOAD_EXAMPLES=False

echo "── Installing Airflow + Cosmos ──────────────────────────────────────────"
pip install "apache-airflow[snowflake]==2.8.0" astronomer-cosmos great_expectations

echo "── Initialising Airflow DB ──────────────────────────────────────────────"
airflow db init

echo "── Creating admin user ──────────────────────────────────────────────────"
airflow users create \
    --username admin \
    --password admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@local

echo "── Copying DAGs and plugins ─────────────────────────────────────────────"
mkdir -p "$AIRFLOW_HOME/dags" "$AIRFLOW_HOME/plugins"
cp airflow/dags/*.py        "$AIRFLOW_HOME/dags/"
cp airflow/plugins/*.py     "$AIRFLOW_HOME/plugins/"

echo "── Adding Snowflake connection ──────────────────────────────────────────"
airflow connections add 'snowflake_cancredit' \
    --conn-type 'snowflake' \
    --conn-host "${SNOWFLAKE_ACCOUNT}.snowflakecomputing.com" \
    --conn-login "${SNOWFLAKE_USER}" \
    --conn-password "${SNOWFLAKE_PASSWORD}" \
    --conn-extra "{\"database\": \"CANCREDIT_DB\", \"warehouse\": \"CANCREDIT_WH\", \"role\": \"SYSADMIN\"}"

echo "── Starting Airflow (webserver + scheduler) ─────────────────────────────"
airflow webserver --port 8080 --daemon
airflow scheduler --daemon

echo ""
echo "✅  Airflow is running at http://localhost:8080  (admin / admin)"
echo "    Manually trigger both DAGs from the UI to validate the pipeline."
