# Design Discussion: Real-Time Fraud Engine

## 1. Latency vs accuracy
- Latency budget is spent on one DynamoDB read (user history) + tree scoring + one conditional write + one history write.
- Model is deliberately small (XGBoost, depth 4, 200 trees) and scored by a dependency-free evaluator inside Lambda. Parity vs XGBoost: max diff 5e-07.
- Accuracy gain came from features, not model size: PR-AUC 0.135 -> 0.482 by adding user history and velocity features. Each such feature costs a lookup, so every new feature must justify its latency.
- Trade-off rule: add a feature only if it improves PR-AUC meaningfully and can be served from the same single read.
- Option if latency tightens: score synchronously with the cheap model, run heavier checks asynchronously and act after the fact (e.g. hold settlement).
- Measured Lambda REPORT lines (first partial replay, 512 MB, ~93 MB used): invocations took ~15-20 ms or ~190-270 ms depending on batch size, which REPORT does not show. Each record costs 3 DynamoDB calls (1 read, 2 writes), so a full batch of 10 is dominated by those 30 calls. Cold starts add ~400-510 ms init (billed). Per-transaction latency still to be measured by logging it in the handler.

## 2. False positives
- At the 0.5 threshold, precision is 8.3%: about 11 of 12 flagged transactions are legitimate. OTP rate is ~3.6% of all traffic.
- Cost model (assumed): missed fraud = 500, false alarm = 5. Total cost was lowest near thresholds 0.3 to 0.5, so recall is cheap to buy but friction is paid by customers.
- Tiering reduces damage: BLOCK only at score > 0.98 (precision ~57% on replay), OTP for the middle band (cheap, reversible), approve the rest.
- Levers to cut false positives: better features, per-segment thresholds, allow-lists for trusted devices, step-up auth instead of block.
- Caveat: the cost numbers are assumptions; real ones come from finance and support data.

## 3. Availability
- SQS FIFO makes ingestion durable; Lambda scales with the queue; DynamoDB is on-demand.
- FIFO message group = user_id keeps one user's transactions ordered (needed for velocity features). A very hot user serializes on one group.
- Idempotent writes (conditional put on transaction_id) make redelivery safe.
- Gaps (not built): dead-letter queue, retry/backoff policy tested under failure, multi-region, a fail-open vs fail-closed rule when scoring is down.
- Failure policy to decide: fail-open for low value (approve + log), hold or step-up for high value.

## 4. Threshold strategy
- Thresholds come from a cost curve, not a fixed 0.5. Current: BLOCK > 0.98, OTP > 0.5.
- Honest limit: thresholds were examined on the test set. In production, tune on a separate validation window.
- Review/OTP capacity is a constraint: threshold should keep the flagged volume within what support and customers can handle.
- Re-tune after drift. Drift demo: PSI 0.014 -> 1.03 and OTP rate 3.6% -> 12.2%, so alarms fired on PSI and OTP rate (BlockRate stayed under its alarm).
- Labels arrive late, so precision/recall are delayed metrics. Rate and PSI alarms are the early warning.

## 5. Short answers for interviews
- Why not accuracy? 99.46% accuracy is reachable by flagging nothing. Use PR-AUC, recall at a precision level, and cost.
- Why SQS not Kinesis? Kinesis was blocked by an organization SCP on my account. SQS FIFO gave per-user ordering; Kinesis would suit higher throughput and replay.
- How do you know serving matches training? Same feature logic, a parity test for the model, and replay PR-AUC 0.481 vs offline 0.482.
- What would you do next? DLQ, validation-based thresholds, SageMaker for training/hosting, real label feedback loop.
