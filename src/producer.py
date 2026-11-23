import json, sys
import boto3
import pandas as pd

sqs = boto3.client("sqs", region_name="ap-southeast-2")
url = sqs.get_queue_url(QueueName="fraud-transactions.fifo")["QueueUrl"]

n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
df = pd.read_csv("data/transactions.csv", parse_dates=["timestamp"])
df = df.sort_values("timestamp").tail(n)   # sabse latest n transactions
records = json.loads(df.to_json(orient="records", date_format="iso"))

for i in range(0, len(records), 10):          # SQS batch limit = 10
    entries = [
        {
            "Id": str(j),
            "MessageBody": json.dumps(r),
            "MessageGroupId": str(r["user_id"]),            # single user tx order me
            "MessageDeduplicationId": str(r["transaction_id"]),
        }
        for j, r in enumerate(records[i:i + 10])
    ]
    resp = sqs.send_message_batch(QueueUrl=url, Entries=entries)
    if resp.get("Failed"):
        print("FAILED:", resp["Failed"])

print("sent", len(records))