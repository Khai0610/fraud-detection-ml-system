import json
import joblib
import pandas as pd

from rule_engine import apply_rules


model = joblib.load("artifacts/model.pkl")

with open("artifacts/feature_columns.json", "r", encoding="utf-8") as f:
    FEATURE_COLUMNS = json.load(f)


def build_features(tx):
    tx["orig_balance_diff"] = tx["oldbalanceOrg"] - tx["newbalanceOrig"]
    tx["dest_balance_diff"] = tx["newbalanceDest"] - tx["oldbalanceDest"]
    tx["hour"] = tx["step"] % 24
    tx["orig_drained"] = int(tx["newbalanceOrig"] == 0)
    tx["new_destination"] = int(tx["oldbalanceDest"] == 0)
    tx["amount_to_balance_ratio"] = tx["amount"] / (tx["oldbalanceOrg"] + 1)

    return tx


def predict_transaction(tx):
    tx = build_features(tx)

    df = pd.DataFrame([tx])

    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = 0

    X = df[FEATURE_COLUMNS]

    model_score = float(model.predict_proba(X)[0][1])

    rule_result = apply_rules(tx)
    rule_score = float(rule_result["rule_score"])

    final_score = 0.7 * model_score + 0.3 * rule_score

    if final_score >= 0.7:
        status = "Fraud"
    elif final_score >= 0.4:
        status = "Pending"
    else:
        status = "Safe"

    return {
        "model_score": round(model_score * 100, 2),
        "rule_score": round(rule_score * 100, 2),
        "final_score": round(final_score * 100, 2),
        "derived_status": status,
        "triggered_rules": rule_result["triggered_rules"],
    }
