import joblib
import pandas as pd
import numpy as np

print("=== Loading Models ===")
modelA = joblib.load("models/modelA_credit_rf.joblib")
modelB = joblib.load("models/modelB_toll_rf.joblib")
isoB   = joblib.load("models/modelB_toll_iso.joblib")
credit_scaler = joblib.load("models/credit_scaler.joblib")
toll_scaler   = joblib.load("models/toll_scaler.joblib")
print("✅ Models Loaded Successfully!\n")

# ---------------------- TEST CASES ----------------------

# ========== A) CREDIT CARD FRAUD TESTS ==========
print("=== CREDIT MODEL TEST ===")

# Normal (legit) transaction
credit_normal = pd.DataFrame([[0.0] * 30], columns=[
    "Time","V1","V2","V3","V4","V5","V6","V7","V8","V9",
    "V10","V11","V12","V13","V14","V15","V16","V17","V18",
    "V19","V20","V21","V22","V23","V24","V25","V26","V27","V28","Amount"
])
credit_normal["Amount"] = 120
credit_normal["Time"] = 50000
credit_normal[["Amount","Time"]] = credit_scaler.transform(credit_normal[["Amount","Time"]])

# Fraudulent transaction simulation
credit_fraud = credit_normal.copy()
credit_fraud["Amount"] = 10000  # huge amount anomaly
credit_fraud[["Amount","Time"]] = credit_scaler.transform(credit_fraud[["Amount","Time"]])

# Predict
p_normal = modelA.predict_proba(credit_normal)[0,1]
p_fraud  = modelA.predict_proba(credit_fraud)[0,1]

print(f"Normal Tx Prob(Fraud): {p_normal:.3f}")
print(f"Fraudulent Tx Prob(Fraud): {p_fraud:.3f}\n")

# ========== B) TOLL MODEL TESTS ==========
print("=== TOLL MODEL TEST ===")

# Normal toll transaction
toll_normal = pd.DataFrame([[120, 60, 5, np.sin(2*np.pi*10/24), np.cos(2*np.pi*10/24)]],
                           columns=["amount","speed","inter_arrival","sin_hour","cos_hour"])
X_normal = toll_scaler.transform(toll_normal)
p_toll_normal = modelB.predict_proba(X_normal)[0,1]
iso_normal = 1 if isoB.predict(X_normal)[0] == -1 else 0

# Fraudulent toll (negative amount, impossible speed)
toll_fraud = pd.DataFrame([[-200, 300, 0.5, np.sin(2*np.pi*10/24), np.cos(2*np.pi*10/24)]],
                           columns=["amount","speed","inter_arrival","sin_hour","cos_hour"])
X_fraud = toll_scaler.transform(toll_fraud)
p_toll_fraud = modelB.predict_proba(X_fraud)[0,1]
iso_fraud = 1 if isoB.predict(X_fraud)[0] == -1 else 0

print(f"Normal Toll Prob(Fraud): {p_toll_normal:.3f} | IF Flag: {iso_normal}")
print(f"Fraudulent Toll Prob(Fraud): {p_toll_fraud:.3f} | IF Flag: {iso_fraud}")

# Decision example
threshold = 0.5
if p_toll_fraud > threshold or iso_fraud:
    print("\n🚨 Fraudulent toll detected (BLOCK ACTION)\n")
else:
    print("\n✅ Normal toll transaction (ALLOW ACTION)\n")
