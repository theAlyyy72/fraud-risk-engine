import boto3, numpy as np, pandas as pd

REGION = "ap-southeast-2"
t = boto3.resource("dynamodb", region_name=REGION).Table("fraud-decisions")
items, kw = [], {}
while True:
    r = t.scan(**kw)
    items += r["Items"]
    if "LastEvaluatedKey" not in r:
        break
    kw["ExclusiveStartKey"] = r["LastEvaluatedKey"]

df = pd.DataFrame(items)
for c in ["transaction_id", "risk_score", "is_fraud"]:
    df[c] = df[c].astype(float)

base = df[(df.transaction_id >= 170480) & (df.transaction_id < 190480)]
cur = df[df.transaction_id >= 190480]

edges = np.unique(np.quantile(base.risk_score, np.linspace(0, 1, 11)))
edges[0], edges[-1] = -np.inf, np.inf
b = np.histogram(base.risk_score, edges)[0] / len(base) + 1e-4
c = np.histogram(cur.risk_score, edges)[0] / len(cur) + 1e-4
psi = float(((c - b) * np.log(c / b)).sum())

y = cur.is_fraud == 1
flag = cur.decision != "APPROVE"
tp = int((flag & y).sum())
m = {
    "BlockRate": float((cur.decision == "BLOCK").mean()),
    "OtpRate": float((cur.decision == "OTP_CHALLENGE").mean()),
    "MeanRiskScore": float(cur.risk_score.mean()),
    "ScorePSI": psi,
    "Precision": tp / max(int(flag.sum()), 1),
    "Recall": tp / max(int(y.sum()), 1),
}
print({k: round(v, 4) for k, v in m.items()})

boto3.client("cloudwatch", region_name=REGION).put_metric_data(
    Namespace="FraudEngine",
    MetricData=[{"MetricName": k, "Value": v, "Unit": "None"} for k, v in m.items()])
print("published", len(m), "metrics")
