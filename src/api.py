from datetime import datetime
import json
from typing import List

from fastapi import FastAPI, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from database import (
    get_dashboard_stats,
    get_latest_transactions,
    get_transaction_by_id,
    save_transaction,
    update_analyst_review,
)
from predictor import build_features, predict_transaction
from powerbi import POWER_BI_REPORT_URL, append_transaction_to_powerbi_csv
from rule_engine import RULES, apply_rules


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

RULES_BY_NAME = {rule.get("name"): rule for rule in RULES}

DECISION_STATUS = {
    "confirm_fraud": "Fraud",
    "false_positive": "Safe",
    "needs_review": "Pending",
}

DECISION_LABELS = {
    "confirm_fraud": "Xác nhận gian lận",
    "false_positive": "Cảnh báo sai",
    "needs_review": "Cần xem xét thêm",
}


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, data):
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except RuntimeError:
                disconnected.append(connection)

        for connection in disconnected:
            self.disconnect(connection)


manager = ConnectionManager()


class TransactionInput(BaseModel):
    transaction_id: str
    step: int
    type: str
    nameOrig: str
    amount: float
    oldbalanceOrg: float
    newbalanceOrig: float
    nameDest: str
    oldbalanceDest: float
    newbalanceDest: float


def parse_triggered_rules(value):
    if not value:
        return []

    if isinstance(value, list):
        parsed = value
    else:
        try:
            parsed = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return [
                {"name": item.strip(), "conditions": []}
                for item in str(value).split(",")
                if item.strip()
            ]

    normalized_rules = []

    for item in parsed:
        if isinstance(item, dict):
            normalized_rules.append(item)
        elif isinstance(item, str):
            normalized_rules.append(RULES_BY_NAME.get(item, {"name": item, "conditions": []}))

    return normalized_rules


def has_rule_metrics(rules):
    return any(
        isinstance(rule, dict)
        and rule.get("precision") is not None
        and rule.get("recall") is not None
        and rule.get("lift") is not None
        for rule in rules
    )


def calculate_matched_rules(tx):
    feature_tx = build_features(tx.copy())
    return apply_rules(feature_tx)["triggered_rules"]


def format_datetime(value):
    if isinstance(value, datetime):
        return value.strftime("%m/%d/%Y, %I:%M:%S %p")
    return value or ""


def explain_transaction(tx):
    reasons = []

    if tx.get("newbalanceOrig") == 0 and tx.get("oldbalanceOrg", 0) > 0:
        reasons.append("Số dư người gửi bị rút về 0 sau giao dịch.")

    if tx.get("amount", 0) >= 100000:
        reasons.append("Số tiền giao dịch lớn bất thường.")

    if tx.get("oldbalanceDest") == 0:
        reasons.append("Tài khoản nhận có số dư ban đầu bằng 0, có thể là tài khoản mới.")

    if tx.get("model_score", 0) >= 70:
        reasons.append("ML score cao, mô hình học máy đánh giá rủi ro lớn.")

    if tx.get("rule_score", 0) >= 70:
        reasons.append("Rule score cao, giao dịch khớp luật gian lận tự động.")

    if tx.get("final_score", 0) >= 70:
        reasons.append("Final score vượt ngưỡng cảnh báo rủi ro cao.")

    triggered_names = [
        rule.get("name")
        for rule in tx.get("triggered_rules", [])
        if isinstance(rule, dict) and rule.get("name")
    ]
    if triggered_names:
        reasons.append("Luật được kích hoạt: " + ", ".join(triggered_names) + ".")

    if not reasons:
        reasons.append("Không có dấu hiệu rủi ro rõ ràng từ ML score hoặc rule engine.")

    return reasons


def prepare_transaction(row):
    tx = dict(row)
    tx["triggered_rules"] = parse_triggered_rules(tx.get("triggered_rules"))

    needs_prediction = (
        tx.get("model_score") is None
        or tx.get("rule_score") is None
        or tx.get("final_score") is None
        or tx.get("derived_status") is None
    )

    if needs_prediction:
        result = predict_transaction(tx.copy())
        tx.update(result)
    else:
        tx["hour"] = tx.get("step", 0) % 24

    if tx.get("derived_status") == "Fraud" and not has_rule_metrics(tx["triggered_rules"]):
        matched_rules = calculate_matched_rules(tx)

        if matched_rules:
            tx["triggered_rules"] = matched_rules

    tx["timestamp"] = format_datetime(tx.get("timestamp"))
    tx["reviewed_at"] = format_datetime(tx.get("reviewed_at"))
    tx["analyst_decision_label"] = DECISION_LABELS.get(tx.get("analyst_decision"), "")
    tx["analyst_status"] = tx.get("analyst_status") or "Unreviewed"
    tx["analyst_note"] = tx.get("analyst_note") or tx.get("analyst_notes") or ""
    tx["fraud_reasons"] = explain_transaction(tx)

    return tx


def score_transaction(tx):
    scored_tx = tx.copy()
    result = predict_transaction(scored_tx.copy())
    scored_tx.update(result)
    scored_tx["timestamp"] = datetime.now()
    return scored_tx


@app.get("/")
def dashboard(request: Request):
    transactions = [prepare_transaction(tx) for tx in get_latest_transactions()]
    stats = get_dashboard_stats()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "transactions": transactions,
            "stats": stats,
            "power_bi_report_url": POWER_BI_REPORT_URL,
        },
    )


@app.get("/review/{transaction_id}")
def review_transaction(request: Request, transaction_id: str):
    tx = get_transaction_by_id(transaction_id)

    return templates.TemplateResponse(
        "review.html",
        {
            "request": request,
            "tx": prepare_transaction(tx) if tx else None,
        },
    )


@app.websocket("/ws/transactions")
async def websocket_transactions(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/api/push-transaction")
async def push_transaction_api(tx: TransactionInput):
    scored_tx = score_transaction(tx.model_dump())
    save_transaction(scored_tx)

    realtime_tx = prepare_transaction(scored_tx)
    append_transaction_to_powerbi_csv(realtime_tx)
    await manager.broadcast(realtime_tx)

    return {
        "message": "Transaction processed",
        "transaction": realtime_tx,
    }


@app.get("/power-bi")
def open_power_bi():
    if POWER_BI_REPORT_URL:
        return RedirectResponse(POWER_BI_REPORT_URL)

    return PlainTextResponse(
        "Chưa cấu hình POWER_BI_REPORT_URL. Hãy set biến môi trường POWER_BI_REPORT_URL bằng link report Power BI của bạn.",
        status_code=404,
    )


@app.post("/review/{transaction_id}/decision")
def save_review_decision(
    transaction_id: str,
    decision: str = Form(...),
    analyst_notes: str = Form(""),
):
    update_analyst_review(
        transaction_id=transaction_id,
        decision=decision,
        notes=analyst_notes,
        new_status=DECISION_STATUS.get(decision),
    )
    return RedirectResponse(f"/review/{transaction_id}", status_code=303)


@app.post("/add-transaction")
async def add_transaction_form(
    transaction_id: str = Form(...),
    step: int = Form(...),
    tx_type: str = Form(...),
    nameOrig: str = Form(...),
    amount: float = Form(...),
    oldbalanceOrg: float = Form(...),
    newbalanceOrig: float = Form(...),
    nameDest: str = Form(...),
    oldbalanceDest: float = Form(...),
    newbalanceDest: float = Form(...),
):
    tx = {
        "transaction_id": transaction_id,
        "step": step,
        "type": tx_type,
        "nameOrig": nameOrig,
        "amount": amount,
        "oldbalanceOrg": oldbalanceOrg,
        "newbalanceOrig": newbalanceOrig,
        "nameDest": nameDest,
        "oldbalanceDest": oldbalanceDest,
        "newbalanceDest": newbalanceDest,
    }

    scored_tx = score_transaction(tx)
    save_transaction(scored_tx)

    realtime_tx = prepare_transaction(scored_tx)
    append_transaction_to_powerbi_csv(realtime_tx)
    await manager.broadcast(realtime_tx)

    return RedirectResponse("/", status_code=303)
