import numpy as np, pandas as pd 

rng = np.random.default_rng(42)
N_USERS, N_TX = 5000, 200_000
COUNTRIES = ["IN", "US", "UK", "AE", "SG"]
CATS = ["grocery", "fuel", "restaurant", "electronics",
        "travel", "online_shopping", "atm", "gift_cards"]

home = rng.choice(COUNTRIES, N_USERS, p=[.6, .15, .1, .1, .05])
avg_amt = rng.lognormal(3.5, 0.5, N_USERS)

uid = rng.choice(N_USERS, N_TX)
ts = pd.Timestamp("2026-01-01") + pd.to_timedelta(
    rng.uniform(0, 30 * 86400, N_TX), unit="s")

df = pd.DataFrame({"user_id": uid, "timestamp": ts})
df["amount"] = (avg_amt[uid] * rng.lognormal(0, 0.6, N_TX)).round(2)
df["category"] = rng.choice(CATS, N_TX,  p=[.25, .15, .2, .08, .05, .15, .08, .04])
df["channel"] = rng.choice(["pos", "online", "atm"], N_TX, p = [.55, .4, .05])
abroad = rng.random(N_TX) < 0.04
df["country"] = np.where(abroad, rng.choice(COUNTRIES, N_TX), home[uid])
df["new_device"] = (rng.random(N_TX) < 0.03).astype(int)

# hidden fraud risk (noisy, so model can learn it)
ratio = df.amount / avg_amt[uid]
foreign = df.country.values != home[uid]
night = df.timestamp.dt.hour.isin([0, 1, 2, 3, 4])
risky = df.category.isin(["electronics", "gift_cards", "travel"])
score = (1.2 * (ratio > 3) + 1.5 * foreign + 2 * df.new_device
         +1.2 * night + 1.0 * risky + 0.8 * (df.channel =="online"))
noisy = score + rng.normal(0, 1.2, N_TX)
df["is_fraud"] = (noisy >= np.quantile(noisy, 0.997)).astype(int)

#fraud bursts: repeated transactions by the same user within 5 minutes
fr = df[df.is_fraud == 1].sample(frac=0.4, random_state=1)
bursts = pd.concat([
    fr.assign(timestamp=fr.timestamp + pd.to_timedelta(
        rng.uniform(10, 300, len(fr)), unit="s"))
    for _ in range(2)])

df = pd.concat([df, bursts]).sort_values("timestamp").reset_index(drop=True)
df.insert(0, "transaction_id", df.index)
df.to_csv("data/transactions.csv", index=False)
print(df.shape, "fraud %:", round(df.is_fraud.mean() * 100, 2))