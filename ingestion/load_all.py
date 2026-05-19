from snowflake_loader import load_csv_chunked
import os

CONFIG = {
    'account': os.environ.get('SNOWFLAKE_ACCOUNT', ''),
    'user': os.environ.get('SNOWFLAKE_USER', ''),
    'password': os.environ.get('SNOWFLAKE_PASSWORD', '')
}

TABLES = {
    'APPLICATION_TRAIN':       'data/home-credit/application_train.csv',
    'APPLICATION_TEST':        'data/home-credit/application_test.csv',
    'BUREAU':                  'data/home-credit/bureau.csv',
    'BUREAU_BALANCE':          'data/home-credit/bureau_balance.csv',
    'PREVIOUS_APPLICATION':    'data/home-credit/previous_application.csv',
    'POS_CASH_BALANCE':        'data/home-credit/POS_CASH_balance.csv',
    'INSTALLMENTS_PAYMENTS':   'data/home-credit/installments_payments.csv',
    'CREDIT_CARD_BALANCE':     'data/home-credit/credit_card_balance.csv',
}

if __name__ == "__main__":
    for table, path in TABLES.items():
        print(f"Loading {table}...")
        try:
            load_csv_chunked(path, table, CONFIG)
            print(f"  Done: {table}\n")
        except Exception as e:
            print(f"  Error loading {table}: {e}\n")
