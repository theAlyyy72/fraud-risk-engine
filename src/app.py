import json, time
from collections import defaultdict, deque
from datetime import datetime

import numpy as np
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel
from xgboost import XGBClassifier

cfg = json.load(open("models/config.json"))
home = json.load(open("models/home_country.json"))
model = XGBClassifier()
model.load_model("models/fraud_xgb.json")

# user_id -> [(unix_ts, amount)]  (baad me DynamoDB)
history = defaultdict(lambda: deque(maxlen=1000))

app = FastAPI(title="Fraud Risk Engine")


class Tx(BaseModel):
    user_id: int
    amount: float
    timestamp: datetime
    category: str
    channel: str
    country: str
    new_device: int = 0


@app.post("/score")
def score(tx: Tx):
    t0 = time.perf_counter()
    h = history[tx.user_id]
    ts = tx.timestamp.timestamp()

    row = dict.fromkeys(cfg["columns"], 0)
    row.update(
        amount=tx.amount,
        hour=tx.timestamp.hour,
        new_device=tx.new_device,
        amt_ratio=tx.amount / np.mean([a for _, a in h]) if h else 1.0,
        secs_since_last=ts - h[-1][0] if h else 1e6,
        tx_5min=sum(1 for t, _ in h if ts - t < 300),
        tx_1h=sum(1 for t, _ in h if ts - t < 3600),
        is_foreign=int(tx.country != home.get(str(tx.user_id), tx.country)),
    )
    for k in (f"category_{tx.category}", f"channel_{tx.channel}"):
        if k in row:
            row[k] = 1

    X = pd.DataFrame([row])[cfg["columns"]]
    p = float(model.predict_proba(X)[0, 1])
    decision = ("BLOCK" if p > cfg["block_thr"]
                else "OTP_CHALLENGE" if p > cfg["otp_thr"] else "APPROVE")

    h.append((ts, tx.amount))
    return {"risk_score": round(p, 4), "decision": decision,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2)}


@app.get("/health")
def health():
    return {"status": "ok"}