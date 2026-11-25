#!/bin/bash
# Removes every AWS resource created for the fraud engine (names start with fraud-).
# CloudWatch metrics cannot be deleted; they expire on their own.
export AWS_DEFAULT_REGION=ap-southeast-2
export AWS_PAGER=""

echo "This deletes the fraud-* queue, Lambda, tables, alarms, SNS topic, IAM roles and S3 bucket."
read -r -p "Type yes to continue: " ok
[ "$ok" = "yes" ] || { echo "aborted"; exit 1; }

aws lambda delete-event-source-mapping --uuid 9ccdc06e-ffb6-445d-bcbf-6258529cf008
aws lambda delete-function --function-name fraud-scorer
aws sqs delete-queue --queue-url "$(aws sqs get-queue-url --queue-name fraud-transactions.fifo --query QueueUrl --output text)"
aws dynamodb delete-table --table-name fraud-user-history
aws dynamodb delete-table --table-name fraud-decisions
aws cloudwatch delete-alarms --alarm-names fraud-score-drift fraud-block-rate-spike fraud-otp-rate-spike
aws sns delete-topic --topic-arn arn:aws:sns:ap-southeast-2:697556721603:fraud-alerts
aws iam detach-role-policy --role-name fraud-lambda-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaSQSQueueExecutionRole
aws iam delete-role-policy --role-name fraud-lambda-role --policy-name fraud-ddb-access
aws iam delete-role --role-name fraud-lambda-role
aws iam delete-role-policy --role-name fraud-sagemaker-role --policy-name fraud-sm-access
aws iam delete-role --role-name fraud-sagemaker-role
aws s3 rb s3://fraud-ml-697556721603 --force
aws logs delete-log-group --log-group-name /aws/lambda/fraud-scorer
echo "done"
