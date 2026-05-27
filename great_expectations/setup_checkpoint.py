"""
Great Expectations — Checkpoint configuration for daily pipeline validation.
Run after build_expectations.py to register the checkpoint used by the Airflow DAG.

Usage:
    python great_expectations/setup_checkpoint.py
"""
import great_expectations as gx


def setup_checkpoint():
    ctx = gx.get_context()

    ctx.add_or_update_checkpoint(
        name='cancredit_daily',
        validations=[
            {
                'batch_request': {
                    'datasource_name': 'cancredit_snowflake',
                    'data_asset_name': 'mart_credit_application_fact',
                },
                'expectation_suite_name': 'mart_fact_suite',
            }
        ],
        action_list=[
            {
                'name': 'store_validation_result',
                'action': {'class_name': 'StoreValidationResultAction'},
            },
            {
                'name': 'update_data_docs',
                'action': {'class_name': 'UpdateDataDocsAction'},
            },
        ],
    )
    print("✅ Checkpoint 'cancredit_daily' registered.")


if __name__ == '__main__':
    setup_checkpoint()
