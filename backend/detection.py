import pandas as pd, numpy as np, joblib
from datetime import datetime, timedelta
import warnings
import os
warnings.filterwarnings("ignore")

# Get the directory where this script is located
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")

# === Load ML Models ===
modelA = joblib.load(os.path.join(MODELS_DIR, "modelA_toll_rf.joblib"))
modelB = joblib.load(os.path.join(MODELS_DIR, "modelB_toll_rf.joblib"))
isoB   = joblib.load(os.path.join(MODELS_DIR, "modelB_toll_iso.joblib"))
toll_scaler_v2 = joblib.load(os.path.join(MODELS_DIR, "toll_scaler_v2.joblib"))  # New scaler for model A
toll_scaler    = joblib.load(os.path.join(MODELS_DIR, "toll_scaler.joblib"))    # Original scaler for model B


# === RULE-BASED DETECTION ===
def rule_based_detection(tx):
    flagged = False
    high_conf = False
    reasons = []

    # Rule 1️⃣ — Invalid or negative amount
    if tx.get("amount", 0) <= 0:
        flagged = True; high_conf = True; reasons.append("Invalid amount (<=0)")

    # Rule 2️⃣ — Extremely high toll
    if tx.get("amount", 0) > 5000:
        flagged = True; reasons.append("Abnormally high toll")

    # Rule 3️⃣ — Car being charged more than expected
    if tx.get("vehicle_type") == "CAR" and tx.get("amount", 0) > 300:
        flagged = True; reasons.append("Car charged more than expected")

    # Rule 4️⃣ — Duplicate scan within 1 minute
    last_time = tx.get("last_seen")  # fetched from DB
    if last_time:
        try:
            last_seen_dt = datetime.fromisoformat(str(last_time))
            if datetime.utcnow() - last_seen_dt < timedelta(minutes=1):
                flagged = True
                reasons.append("Duplicate RFID scan within 1 minute")
        except Exception:
            pass  # ignore bad timestamp formats

    return {"flagged": flagged, "high_confidence": high_conf, "reasons": reasons}


# === COMBINED ML + RULE DETECTION ===
def run_detection(tx):
    # Step 1 — Run rule-based logic
    rule_result = rule_based_detection(tx)

    # Step 2 — Prepare toll features
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

    # Step 3 — Toll fraud model for fraud detection using toll features
    # Create a dummy input with the correct number of toll features (5: amount, speed, inter_arrival, sin_hour, cos_hour)
    # Use more meaningful input based on the transaction data
    dummy_credit = np.array([[tx.get("amount", 100), tx.get("speed", 60), tx.get("inter_arrival", 5), 
                             np.sin(2 * np.pi * (datetime.utcnow().hour) / 24), 
                             np.cos(2 * np.pi * (datetime.utcnow().hour) / 24)]])
    dummy_credit_scaled = toll_scaler_v2.transform(dummy_credit)
    pA = modelA.predict_proba(dummy_credit_scaled)[0, 1]

    # Step 4 — Decision fusion
    if rule_result["high_confidence"]:
        action = "block"
    elif iso_flag == 1 and pB > 0.6:
        action = "block"
        rule_result["reasons"].append("Anomaly detected (ML + ISO)")
    elif pB > 0.7:
        action = "block"
        rule_result["reasons"].append("High fraud probability (RF)")
    elif "Duplicate RFID scan within 1 minute" in rule_result["reasons"]:
        action = "block"
    else:
        action = "allow"

    final_flag = (action == "block")

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
