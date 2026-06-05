import csv
import os
from pathlib import Path


POWER_BI_REPORT_URL = os.getenv("POWER_BI_REPORT_URL", "").strip()
POWER_BI_CSV_PATH = Path(os.getenv("POWER_BI_CSV_PATH", "logs/powerbi_transactions.csv"))

CSV_COLUMNS = [
    "transaction_id",
    "step",
    "type",
    "nameOrig",
    "nameDest",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
    "model_score",
    "rule_score",
    "final_score",
    "derived_status",
    "analyst_status",
    "timestamp",
]


def append_transaction_to_powerbi_csv(tx):
    POWER_BI_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_exists = POWER_BI_CSV_PATH.exists() and POWER_BI_CSV_PATH.stat().st_size > 0

    row = {
        "transaction_id": tx.get("transaction_id"),
        "step": tx.get("step"),
        "type": tx.get("type"),
        "nameOrig": tx.get("nameOrig"),
        "nameDest": tx.get("nameDest"),
        "amount": tx.get("amount"),
        "oldbalanceOrg": tx.get("oldbalanceOrg"),
        "newbalanceOrig": tx.get("newbalanceOrig"),
        "oldbalanceDest": tx.get("oldbalanceDest"),
        "newbalanceDest": tx.get("newbalanceDest"),
        "model_score": tx.get("model_score"),
        "rule_score": tx.get("rule_score"),
        "final_score": tx.get("final_score"),
        "derived_status": tx.get("derived_status"),
        "analyst_status": tx.get("analyst_status") or "Unreviewed",
        "timestamp": tx.get("timestamp"),
    }

    with POWER_BI_CSV_PATH.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)

        if not file_exists:
            writer.writeheader()

        writer.writerow(row)
