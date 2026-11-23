import json

def lambda_handler(event, context):
    records = event.get("Records", [])
    for r in records:
        tx = json.loads(r["body"])
        print("got tx", tx["transaction_id"], tx["user_id"], tx["amount"])
    return {"processed": len(records)}
