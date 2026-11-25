import json
import boto3, numpy as np, pandas as pd

lam = boto3.client("lambda", region_name="ap-southeast-2")
df = pd.read_csv("data/transactions.csv", parse_dates=["timestamp"])
d = df.sort_values("timestamp").tail(200).copy()
d["transaction_id"] += 2_000_000
d["timestamp"] += pd.Timedelta(days=14)
recs = json.loads(d.to_json(orient="records", date_format="iso"))

per_rec, calls = [], []
for i in range(0, len(recs), 10):
    ev = {"Records": [{"body": json.dumps(r)} for r in recs[i:i + 10]]}
    r = lam.invoke(FunctionName="fraud-scorer", Payload=json.dumps(ev))
    out = json.loads(r["Payload"].read())
    if "FunctionError" in r:
        raise SystemExit(out)
    per_rec.append(out["ms"])
    calls.append(len(out["ms"]))

first, rest = per_rec[0], [x for b in per_rec[1:] for x in b]
print("records:", sum(calls))
print("first batch (maybe cold) ms:", first)
print("warm per-record ms: p50=%.1f p95=%.1f max=%.1f" %
      (np.percentile(rest, 50), np.percentile(rest, 95), max(rest)))
