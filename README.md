# Real-Time Fraud Detection & Risk Engine
ML + Streaming + AWS. Data synthetic hai (src/generate_data.py).
Flow: Transaction → Stream → Features → XGBoost → Risk Score → Decision → Alert
Results: baseline PR-AUC 0.135 → feature engineering ke baad 0.482
Policy: score > 0.98 BLOCK, > 0.5 OTP_CHALLENGE, baaki APPROVE
