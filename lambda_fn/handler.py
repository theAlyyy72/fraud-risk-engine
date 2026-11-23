import json, os
from datetime import datetime
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError
from xgb_lite import XGBLite

HERE = os.path.dirname(__file__)
cfg = json.load(open(os.path.join(HERE, "config.json")))
home = json.load(open(os.path.join(HERE, "home_country.json")))
model = XGBLite(os.path.join(HERE, "fraud_xgb.json"))
COLS = cfg["columns"]

ddb = boto3.resource("dynamodb")
hist_t = ddb.Table("fraud-user-history")
dec_t = ddb.Table("fraud-decisions")


def build_row(tx, h, ts, dt):
    n = int(h.get("cnt", 0))
    avg = float(h["total"]) / n if n else None
    recent = json.loads(h.get("recent", "[]"))
    row = dict.fromkeys(COLS, 0.0)
    row.update(
        amount=tx["amount"],
        hour=dt.hour,
        new_device=tx["new_device"],
        amt_ratio=tx["amount"] / avg if avg else 1.0,
        secs_since_last=ts - float(h["last_ts"]) if n else 1e6,
        tx_5min=sum(1 for t in recent if ts - t < 300),
        tx_1h=sum(1 for t in recent if ts - t < 3600),
        is_foreign=int(tx["country"] != home.get(str(tx["user_id"]), tx["country"])),
    )
    for k in ("category_" + tx["category"], "channel_" + tx["channel"]):
        if k in row:
            row[k] = 1.0
    return [float(row[c]) for c in COLS], recent


def lambda_handler(event, context):
    done = skipped = 0
    for rec in event.get("Records", []):
        tx = json.loads(rec["body"])
        dt = datetime.fromisoformat(tx["timestamp"].replace("Z", ""))
        ts = dt.timestamp()
        uid = int(tx["user_id"])

        h = hist_t.get_item(Key={"user_id": uid}, ConsistentRead=True).get("Item", {})
        x, recent = build_row(tx, h, ts, dt)
        p = model.predict(x)
        decision = ("BLOCK" if p > cfg["block_thr"]
                    else "OTP_CHALLENGE" if p > cfg["otp_thr"] else "APPROVE")

        try:  # idempotent: duplicate delivery ko skip karo
            dec_t.put_item(
                Item={"transaction_id": int(tx["transaction_id"]), "user_id": uid,
                      "amount": Decimal(str(tx["amount"])),
                      "risk_score": Decimal(str(round(p, 4))),
                      "decision": decision, "ts": tx["timestamp"],
                      "is_fraud": int(tx.get("is_fraud", 0))},
                ConditionExpression="attribute_not_exists(transaction_id)")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                skipped += 1
                continue
            raise

        recent = [t for t in recent if ts - t < 3600] + [ts]
        hist_t.put_item(Item={
            "user_id": uid, "cnt": int(h.get("cnt", 0)) + 1,
            "total": Decimal(str(float(h.get("total", 0)) + tx["amount"])),
            "last_ts": Decimal(str(ts)), "recent": json.dumps(recent[-200:])})

        print(json.dumps({"tx": tx["transaction_id"], "user": uid,
                          "score": round(p, 4), "decision": decision}))
        done += 1
    return {"processed": done, "skipped": skipped}
