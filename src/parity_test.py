import json, sys, random
import numpy as np
sys.path.insert(0, "lambda_fn")
from xgb_lite import XGBLite
from xgboost import XGBClassifier

cols = json.load(open("models/config.json"))["columns"]
rng = {"amount": (0, 1000), "hour": (0, 23), "amt_ratio": (0, 10),
       "secs_since_last": (0, 1e6), "tx_5min": (0, 6), "tx_1h": (0, 20)}
X = np.array([[random.uniform(*rng[c]) if c in rng else random.randint(0, 1)
               for c in cols] for _ in range(500)], dtype=np.float32)

m = XGBClassifier()
m.load_model("models/fraud_xgb.json")
ref = m.predict_proba(X)[:, 1]
lite = XGBLite("models/fraud_xgb.json")
mine = np.array([lite.predict([float(v) for v in row]) for row in X])
print("max abs diff:", float(np.abs(ref - mine).max()))
