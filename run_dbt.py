import os
import subprocess
from dotenv import load_dotenv
import sys

load_dotenv()

# Add python scripts folder to path to find dbt
os.environ["PATH"] += os.pathsep + os.path.expanduser("~\\AppData\\Roaming\\Python\\Python312\\Scripts")

def run(cmd):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        sys.exit(result.returncode)

if __name__ == "__main__":
    run("dbt deps --project-dir dbt/cancredit")
    run("dbt run --project-dir dbt/cancredit")
    run("dbt test --project-dir dbt/cancredit")
