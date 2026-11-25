import pandas as pd, numpy as np
df = pd.read_csv("data/transactions.csv", parse_dates=["timestamp"])
d = df.sort_values("timestamp").tail(5000).copy()
rng = np.random.default_rng(7)
d["transaction_id"] += 1_000_000
d["timestamp"] += pd.Timedelta(days=7)
d["amount"] = (d["amount"] * 4).round(2)
d["new_device"] = (rng.random(len(d)) < 0.25).astype(int)
d["country"] = rng.choice(["US", "UK", "AE", "SG", "IN"], len(d))
d.to_csv("data/drift.csv", index=False)
print("drift rows:", len(d))
