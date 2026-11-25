# Real-Time Fraud Detection & Risk Engine

ML + streaming + AWS. Transaction aate hi score hota hai, decision banta hai, aur monitoring drift pakadti hai.

Flow: Producer -> SQS FIFO -> Lambda (features + XGBoost) -> DynamoDB -> CloudWatch metrics -> Alarms -> SNS alert

## Results (synthetic data, time-based split)
- Baseline (raw features): PR-AUC 0.135
- + Feature engineering (user history, velocity): PR-AUC 0.482
- AWS replay, last 10k transactions: PR-AUC 0.481, recall 80% (32/40 fraud), precision 8.3%
- BLOCK tier only: precision 57%, recall 42%
- Lambda scoring: ~2-3 ms per batch of 10 (model evaluator, no heavy libs)
- Offline vs AWS score parity: max diff 5e-07

## Decision policy
score > 0.98 BLOCK, score > 0.5 OTP_CHALLENGE, else APPROVE.
Thresholds chosen from cost analysis (missed fraud 100x costlier than a false alarm, assumed costs).

## Monitoring
CloudWatch namespace FraudEngine: BlockRate, OtpRate, MeanRiskScore, ScorePSI, Precision, Recall.
Drift demo (4x amounts, more new devices): PSI 0.014 -> 1.03, OTP rate 3.6% -> 12.2%, drift + OTP alarms fired.

## Design decisions
- FIFO queue grouped by user_id keeps one user's transactions in order (needed for velocity features).
- Idempotent writes (conditional put) so duplicate deliveries are skipped.
- XGBoost model JSON evaluated by a small dependency-free scorer inside Lambda, verified by a parity test.
- Features use only past data, same code path in training and serving.

## Honest limitations
- Data is synthetic. Fraud rate is 0.54%, and the evaluation window has only 40 frauds, so precision/recall are noisy.
- Kinesis was blocked by the organization policy (SCP) on my account, so I used SQS FIFO. Kinesis would suit higher throughput and replay.
- SageMaker and Kafka are not used yet.
- Precision/Recall need fraud labels, which arrive late in real life, so rate/drift alarms come first.

## Run
python src/generate_data.py, then the notebook for training, then src/producer.py, src/evaluate.py, src/monitor.py.
Needs AWS login (ap-southeast-2).
