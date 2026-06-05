from datetime import datetime
import json
import os
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text


DB_USER = os.getenv("MYSQL_USER", "root")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "NgoKhai@610")
DB_HOST = os.getenv("MYSQL_HOST", "localhost")
DB_PORT = os.getenv("MYSQL_PORT", "3306")
DB_NAME = os.getenv("MYSQL_DATABASE", "fraud_detection_db")

DATABASE_URL = (
    f"mysql+pymysql://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def serialize_rules(rules):
    return json.dumps(rules or [], ensure_ascii=False)


def save_transaction(tx):
    query = text(
        """
        INSERT INTO transactions (
            transaction_id,
            step,
            type,
            nameOrig,
            amount,
            oldbalanceOrg,
            newbalanceOrig,
            nameDest,
            oldbalanceDest,
            newbalanceDest,
            model_score,
            rule_score,
            final_score,
            derived_status,
            triggered_rules,
            timestamp
        )
        VALUES (
            :transaction_id,
            :step,
            :type,
            :nameOrig,
            :amount,
            :oldbalanceOrg,
            :newbalanceOrig,
            :nameDest,
            :oldbalanceDest,
            :newbalanceDest,
            :model_score,
            :rule_score,
            :final_score,
            :derived_status,
            :triggered_rules,
            :timestamp
        )
        """
    )

    data = tx.copy()
    data["triggered_rules"] = serialize_rules(data.get("triggered_rules"))
    data["timestamp"] = data.get("timestamp") or datetime.now()

    with engine.begin() as conn:
        conn.execute(query, data)


def get_latest_transactions(limit=100):
    query = text(
        """
        SELECT *
        FROM transactions
        ORDER BY COALESCE(timestamp, '1970-01-01') DESC, id DESC
        LIMIT :limit
        """
    )

    with engine.begin() as conn:
        rows = conn.execute(query, {"limit": limit}).mappings().all()

    return [dict(row) for row in rows]


def get_dashboard_stats():
    summary_query = text(
        """
        SELECT
            COUNT(*) AS total_transactions,
            SUM(CASE WHEN derived_status = 'Fraud' THEN 1 ELSE 0 END) AS fraud_count,
            SUM(CASE WHEN derived_status = 'Safe' THEN 1 ELSE 0 END) AS safe_count,
            SUM(CASE WHEN derived_status = 'Pending' THEN 1 ELSE 0 END) AS pending_count,
            COALESCE(SUM(CASE WHEN derived_status = 'Fraud' THEN amount ELSE 0 END), 0) AS fraud_amount
        FROM transactions
        """
    )
    top_sender_query = text(
        """
        SELECT nameOrig AS account, COUNT(*) AS total, COALESCE(SUM(amount), 0) AS amount
        FROM transactions
        WHERE derived_status IN ('Fraud', 'Pending') OR final_score >= 70
        GROUP BY nameOrig
        ORDER BY total DESC, amount DESC
        LIMIT 5
        """
    )
    top_receiver_query = text(
        """
        SELECT nameDest AS account, COUNT(*) AS total, COALESCE(SUM(amount), 0) AS amount
        FROM transactions
        WHERE derived_status IN ('Fraud', 'Pending') OR final_score >= 70
        GROUP BY nameDest
        ORDER BY total DESC, amount DESC
        LIMIT 5
        """
    )

    with engine.begin() as conn:
        summary = dict(conn.execute(summary_query).mappings().first())
        top_senders = [dict(row) for row in conn.execute(top_sender_query).mappings().all()]
        top_receivers = [dict(row) for row in conn.execute(top_receiver_query).mappings().all()]

    total = summary.get("total_transactions") or 0
    fraud_count = summary.get("fraud_count") or 0
    summary["safe_count"] = summary.get("safe_count") or 0
    summary["pending_count"] = summary.get("pending_count") or 0
    summary["fraud_amount"] = float(summary.get("fraud_amount") or 0)
    summary["fraud_rate"] = round((fraud_count / total * 100), 2) if total else 0
    summary["top_senders"] = top_senders
    summary["top_receivers"] = top_receivers

    return summary


def get_transaction_by_id(transaction_id):
    query = text(
        """
        SELECT *
        FROM transactions
        WHERE transaction_id = :transaction_id
        LIMIT 1
        """
    )

    with engine.begin() as conn:
        row = conn.execute(query, {"transaction_id": transaction_id}).mappings().first()

    return dict(row) if row else None


def update_analyst_review(transaction_id, decision, notes, new_status=None):
    analyst_status = {
        "confirm_fraud": "Confirmed Fraud",
        "false_positive": "False Positive",
        "needs_review": "Needs More Review",
    }.get(decision, "Unreviewed")

    if new_status:
        query = text(
            """
            UPDATE transactions
            SET
                derived_status = :derived_status,
                analyst_decision = :analyst_decision,
                analyst_notes = :analyst_notes,
                analyst_status = :analyst_status,
                analyst_note = :analyst_note,
                reviewed_at = :reviewed_at
            WHERE transaction_id = :transaction_id
            """
        )
        params = {
            "derived_status": new_status,
            "analyst_decision": decision,
            "analyst_notes": notes,
            "analyst_status": analyst_status,
            "analyst_note": notes,
            "reviewed_at": datetime.now(),
            "transaction_id": transaction_id,
        }
    else:
        query = text(
            """
            UPDATE transactions
            SET
                analyst_notes = :analyst_notes,
                analyst_note = :analyst_note,
                reviewed_at = :reviewed_at
            WHERE transaction_id = :transaction_id
            """
        )
        params = {
            "analyst_notes": notes,
            "analyst_note": notes,
            "reviewed_at": datetime.now(),
            "transaction_id": transaction_id,
        }

    with engine.begin() as conn:
        conn.execute(query, params)
