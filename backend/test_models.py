import joblib
import pandas as pd
import numpy as np

print("=== Loading Models ===")
modelA = joblib.load("../models/modelA_toll_rf.joblib")
modelB = joblib.load("../models/modelB_toll_rf.joblib")
isoB   = joblib.load("../models/modelB_toll_iso.joblib")
toll_scaler_v2 = joblib.load("../models/toll_scaler_v2.joblib")
toll_scaler   = joblib.load("../models/toll_scaler.joblib")
print("✅ Models Loaded Successfully!\n")

# ---------------------- TEST CASES ----------------------

# ========== A) TOLL FRAUD TESTS ==========
print("=== TOLL MODEL A TEST ===")

# Load a real sample from the toll fraud dataset to use as baseline
toll_df = pd.read_csv("../data/toll_fraud_dataset.csv")  # relative to project root from backend dir
feature_cols = [col for col in toll_df.columns if col not in ['Class']]

# Normal (legit) transaction - use actual feature values from a legitimate transaction
sample_legit = toll_df[toll_df['Class'] == 0].iloc[0][feature_cols].values.reshape(1, -1)
toll_normal = pd.DataFrame(sample_legit, columns=feature_cols)
toll_normal = pd.DataFrame(toll_scaler_v2.transform(toll_normal), columns=feature_cols)

# Fraudulent transaction simulation - use actual feature values from a fraudulent transaction
try:
    sample_fraud = toll_df[toll_df['Class'] == 1].iloc[0][feature_cols].values.reshape(1, -1)
    toll_fraud = pd.DataFrame(sample_fraud, columns=feature_cols)
    toll_fraud = pd.DataFrame(toll_scaler_v2.transform(toll_fraud), columns=feature_cols)
except IndexError:
    # If no fraud samples found, modify legit sample to create a fraud-like scenario
    toll_fraud = toll_normal.copy()
    # Modify some features to make it more fraud-like (Amount is the first column)
    if len(toll_fraud.columns) > 0:
        toll_fraud.iloc[0, 0] = toll_fraud.iloc[0, 0] + 50.0  # Increase Amount feature

# Predict
p_normal = modelA.predict_proba(toll_normal)[0,1]
p_fraud  = modelA.predict_proba(toll_fraud)[0,1]

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

print(f"Normal Toll Prob(Fraud): {p_toll_normal:.3f} | IF Flag: {iso_fraud}")
print(f"Fraudulent Toll Prob(Fraud): {p_toll_fraud:.3f} | IF Flag: {iso_fraud}")

# Decision example
threshold = 0.5
if p_toll_fraud > threshold or iso_fraud:
    print("\n🚨 Fraudulent toll detected (BLOCK ACTION)\n")
else:
    print("\n✅ Normal toll transaction (ALLOW ACTION)\n")