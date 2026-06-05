import random
import time

import requests


API_URL = "http://127.0.0.1:8001/api/push-transaction"

SCENARIOS = [
    ("safe_small", 0.40),
    ("safe_large_balance", 0.12),
    ("ml_pending_no_rule", 0.14),
    ("rule_2_large_not_drained", 0.10),
    ("rule_3_small_full_drain", 0.08),
    ("rule_4_full_drain_low_dest_change", 0.08),
    ("rule_5_full_drain_high_dest_change", 0.08),
]


def random_account(prefix="C"):
    return prefix + str(random.randint(100000000, 999999999))


def pick_scenario():
    names = [name for name, _ in SCENARIOS]
    weights = [weight for _, weight in SCENARIOS]
    return random.choices(names, weights=weights, k=1)[0]


def generate_transaction(i):
    scenario = pick_scenario()

    if scenario == "safe_small":
        amount = round(random.uniform(100, 10000), 2)
        oldbalance_org = round(random.uniform(amount, 100000), 2)
        newbalance_orig = round(oldbalance_org - amount, 2)
        oldbalance_dest = round(random.uniform(0, 50000), 2)
        newbalance_dest = round(oldbalance_dest + amount, 2)

    elif scenario == "safe_large_balance":
        amount = round(random.uniform(20000, 900000), 2)
        oldbalance_org = round(random.uniform(amount * 2.2, amount * 5), 2)
        newbalance_orig = round(oldbalance_org - amount * random.uniform(0.2, 0.55), 2)
        oldbalance_dest = round(random.uniform(1000, 250000), 2)
        newbalance_dest = round(oldbalance_dest + amount * random.uniform(0.1, 0.7), 2)

    elif scenario == "ml_pending_no_rule":
        amount = round(random.uniform(650000, 980000), 2)
        oldbalance_org = round(random.uniform(amount * 1.25, amount * 1.85), 2)
        newbalance_orig = round(random.uniform(amount * 0.35, amount * 0.95), 2)
        oldbalance_dest = round(random.uniform(0, 500), 2)
        newbalance_dest = round(random.uniform(0, amount * 0.55), 2)

    elif scenario == "rule_2_large_not_drained":
        amount = round(random.uniform(1000000, 1700000), 2)
        oldbalance_org = round(random.uniform(amount * 1.05, amount * 2.3), 2)
        newbalance_orig = round(random.uniform(amount * 0.8, oldbalance_org), 2)
        oldbalance_dest = round(random.uniform(0, 200), 2)
        newbalance_dest = round(random.uniform(1000, 820000), 2)

    elif scenario == "rule_3_small_full_drain":
        amount = round(random.uniform(120, 1100), 2)
        oldbalance_org = amount
        newbalance_orig = 0.0
        oldbalance_dest = round(random.uniform(0, 1000), 2)
        newbalance_dest = round(random.uniform(0, 500), 2)

    elif scenario == "rule_4_full_drain_low_dest_change":
        amount = round(random.uniform(5000, 220000), 2)
        oldbalance_org = amount
        newbalance_orig = 0.0
        oldbalance_dest = round(random.uniform(0, 90000), 2)
        newbalance_dest = round(oldbalance_dest + random.uniform(0, 600), 2)

    else:
        amount = round(random.uniform(80000, 350000), 2)
        oldbalance_org = amount
        newbalance_orig = 0.0
        oldbalance_dest = round(random.uniform(0, 1000), 2)
        newbalance_dest = round(oldbalance_dest + amount, 2)

    return {
        "transaction_id": f"TXN-STREAM-{int(time.time())}-{i}-{random.randint(1000, 9999)}",
        "step": random.randint(1, 744),
        "type": random.choice(["TRANSFER", "CASH_OUT"]),
        "nameOrig": random_account("C"),
        "amount": amount,
        "oldbalanceOrg": oldbalance_org,
        "newbalanceOrig": newbalance_orig,
        "nameDest": random_account("C"),
        "oldbalanceDest": oldbalance_dest,
        "newbalanceDest": newbalance_dest,
    }


def main():
    print("Starting realtime bank transaction stream...")

    for i in range(1, 101):
        tx = generate_transaction(i)

        try:
            response = requests.post(API_URL, json=tx, timeout=10)
            response.raise_for_status()

            result = response.json()["transaction"]

            print(
                f"{result['transaction_id']} | "
                f"{result['type']} | "
                f"amount={result['amount']} | "
                f"status={result['derived_status']} | "
                f"ml_score={result['model_score']} | "
                f"rule_score={result['rule_score']} | "
                f"final_score={result['final_score']}"
            )

        except Exception as exc:
            print("Error pushing transaction:", exc)

        time.sleep(2)


if __name__ == "__main__":
    main()
