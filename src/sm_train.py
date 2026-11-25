import time

import boto3
import pandas as pd

REGION = "ap-southeast-2"
BUCKET = "fraud-ml-697556721603"
ROLE = "arn:aws:iam::697556721603:role/fraud-sagemaker-role"
IMAGE = "783357654285.dkr.ecr.ap-southeast-2.amazonaws.com/sagemaker-xgboost:1.7-1"

# class imbalance weight, computed from the training labels (first column)
y = pd.read_csv("data/sm/train.csv", header=None, usecols=[0])[0]
spw = (y == 0).sum() / (y == 1).sum()


def channel(name):
    return {
        "ChannelName": name,
        "ContentType": "text/csv",
        "DataSource": {"S3DataSource": {
            "S3DataType": "S3Prefix",
            "S3Uri": f"s3://{BUCKET}/xgb/{name}/",
            "S3DataDistributionType": "FullyReplicated"}},
    }


sm = boto3.client("sagemaker", region_name=REGION)
job = "fraud-xgb-" + time.strftime("%Y%m%d-%H%M%S")
sm.create_training_job(
    TrainingJobName=job,
    RoleArn=ROLE,
    AlgorithmSpecification={"TrainingImage": IMAGE, "TrainingInputMode": "File"},
    HyperParameters={"objective": "binary:logistic", "num_round": "200",
                     "max_depth": "4", "eta": "0.1",
                     "scale_pos_weight": str(round(float(spw), 2)),
                     "eval_metric": "aucpr"},
    InputDataConfig=[channel("train"), channel("validation")],
    OutputDataConfig={"S3OutputPath": f"s3://{BUCKET}/xgb/output"},
    ResourceConfig={"InstanceType": "ml.m5.large", "InstanceCount": 1,
                    "VolumeSizeInGB": 5},
    StoppingCondition={"MaxRuntimeInSeconds": 900},
)
print("started", job)

while True:
    d = sm.describe_training_job(TrainingJobName=job)
    status = d["TrainingJobStatus"]
    print(status, d.get("SecondaryStatus"))
    if status in ("Completed", "Failed", "Stopped"):
        break
    time.sleep(30)

print("failure reason:", d.get("FailureReason"))
for m in d.get("FinalMetricDataList", []):
    print(m["MetricName"], m["Value"])
print("model:", d.get("ModelArtifacts", {}).get("S3ModelArtifacts"))
