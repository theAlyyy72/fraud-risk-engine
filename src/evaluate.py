import boto3, pandas as pd
from sklearn.metrics import average_precision_score

t = boto3.resource("dynamodb", region_name="ap-southeast-2").Table("fraud-decisions")
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
print("total decisions:", len(df))
df = df[df.transaction_id >= 190480]          # sirf aakhri 10k (warm-ish)
if len(df) == 0:
    raise SystemExit("The Last 10K have not been processed yet. Please wait a little.")
y = df.is_fraud == 1
print("evaluated:", len(df), "| frauds:", int(y.sum()))
print("PR-AUC:", round(average_precision_score(y, df.risk_score), 4))
for name, mask in [("OTP+BLOCK", df.decision != "APPROVE"), ("BLOCK only", df.decision == "BLOCK")]:
    tp = int((mask & y).sum())
    print(f"{name}: flagged={int(mask.sum())} caught={tp} "
          f"precision={tp/max(int(mask.sum()),1):.3f} recall={tp/max(int(y.sum()),1):.3f}")
