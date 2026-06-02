import os
import sys
from load_raw import load_table

TABLES = {
    "BUREAU_BALANCE":          "data/home-credit/bureau_balance.csv",
    "PREVIOUS_APPLICATION":    "data/home-credit/previous_application.csv",
    "POS_CASH_BALANCE":        "data/home-credit/POS_CASH_balance.csv",
    "INSTALLMENTS_PAYMENTS":   "data/home-credit/installments_payments.csv",
    "CREDIT_CARD_BALANCE":     "data/home-credit/credit_card_balance.csv",
}

if __name__ == "__main__":
    for table, path in TABLES.items():
        print(f"\nLoading {table}...")
        try:
            load_table(table, path)
        except Exception as e:
            print(f"  ERROR loading {table}: {e}\n")
