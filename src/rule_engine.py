import json


with open("artifacts/validated_rules.json", "r", encoding="utf-8") as f:
    RULES = json.load(f)


def evaluate_condition(value, operator, threshold):
    if operator == "<=":
        return value <= threshold
    if operator == ">":
        return value > threshold
    if operator == "==":
        return value == threshold
    return False


def apply_rules(transaction):
    triggered_rules = []
    total_score = 0.0

    for rule in RULES:
        matched = True

        for feature, operator, threshold in rule["conditions"]:
            value = transaction.get(feature, 0)

            if not evaluate_condition(value, operator, threshold):
                matched = False
                break

        if matched:
            triggered_rules.append(rule)
            total_score += rule.get("weight", 0.5)

    rule_score = total_score / len(triggered_rules) if triggered_rules else 0.0

    return {
        "rule_score": float(rule_score),
        "triggered_rules": triggered_rules,
    }
