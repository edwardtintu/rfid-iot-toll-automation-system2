import pandas as pd, numpy as np, joblib
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

# === Load ML Models ===
modelA = joblib.load("models/modelA_credit_rf.joblib")
modelB = joblib.load("models/modelB_toll_rf.joblib")
isoB   = joblib.load("models/modelB_toll_iso.joblib")
credit_scaler = joblib.load("models/credit_scaler.joblib")
toll_scaler   = joblib.load("models/toll_scaler.joblib")

# === Rule-based logic ===
def rule_based_detection(tx):
    flagged = False
    high_conf = False
    reasons = []

    # Simple logical checks
    if tx.get("amount", 0) <= 0:
        flagged = True; high_conf = True; reasons.append("Invalid amount (<=0)")
    if tx.get("speed", 0) <= 0 or tx["speed"] > 200:
        flagged = True; high_conf = True; reasons.append("Unrealistic speed")
    if tx.get("inter_arrival", 5) < 2:
        flagged = True; reasons.append("Duplicate RFID entry too soon")
    if tx.get("amount", 0) > 5000:
        flagged = True; reasons.append("Abnormally high toll")
    if tx.get("vehicle_type") == "CAR" and tx.get("amount", 0) > 300:
        flagged = True; reasons.append("Car charged more than expected")

    return {"flagged": flagged, "high_confidence": high_conf, "reasons": reasons}


# === Combined ML + Rule Detection ===
def run_detection(tx):
    # Step 1: Rule check
    rule_result = rule_based_detection(tx)

    # Step 2: ML feature prep for toll dataset
    toll_feat = pd.DataFrame([[
        tx.get("amount", 100),
        tx.get("speed", 60),
        tx.get("inter_arrival", 5),
        np.sin(2 * np.pi * (datetime.utcnow().hour) / 24),
        np.cos(2 * np.pi * (datetime.utcnow().hour) / 24)
    ]], columns=["amount", "speed", "inter_arrival", "sin_hour", "cos_hour"])

    X_toll = toll_scaler.transform(toll_feat)
    pB = modelB.predict_proba(X_toll)[0, 1]
    iso_flag = 1 if isoB.predict(X_toll)[0] == -1 else 0

    # Step 3: Credit model (not directly used but part of hybrid logic)
    dummy_credit = np.zeros((1, 30))
    pA = modelA.predict_proba(dummy_credit)[0, 1]

    # Step 4: Decision fusion
    final_flag = rule_result["flagged"] or (pB > 0.5) or iso_flag
    action = "block" if (rule_result["high_confidence"] or pB > 0.7 or iso_flag) else "allow"

    return {
        "flagged": bool(final_flag),
        "action": action,
        "reasons": rule_result["reasons"],
        "ml_scores": {
            "modelA_prob": round(float(pA), 3),
            "modelB_prob": round(float(pB), 3),
            "iso_flag": int(iso_flag)
        }
    }
