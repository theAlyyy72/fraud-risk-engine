import json, sys
from concurrent.futures import ThreadPoolExecutor
import boto3
import pandas as pd

sqs = boto3.client("sqs", region_name="ap-southeast-2")
url = sqs.get_queue_url(QueueName="fraud-transactions.fifo")["QueueUrl"]

n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
df = pd.read_csv(sys.argv[2] if len(sys.argv) > 2 else "data/transactions.csv", parse_dates=["timestamp"])
df = df.sort_values("timestamp").tail(n)
records = json.loads(df.to_json(orient="records", date_format="iso"))

SHARDS = 8

def send_shard(k):
    mine = [r for r in records if r["user_id"] % SHARDS == k]
    for i in range(0, len(mine), 10):
        entries = [{"Id": str(j), "MessageBody": json.dumps(r),
                    "MessageGroupId": str(r["user_id"]),
                    "MessageDeduplicationId": str(r["transaction_id"])}
                   for j, r in enumerate(mine[i:i + 10])]
        resp = sqs.send_message_batch(QueueUrl=url, Entries=entries)
        if resp.get("Failed"):
            print("FAILED:", resp["Failed"])
    return len(mine)

with ThreadPoolExecutor(SHARDS) as ex:
    sent = sum(ex.map(send_shard, range(SHARDS)))
print("sent", sent)
