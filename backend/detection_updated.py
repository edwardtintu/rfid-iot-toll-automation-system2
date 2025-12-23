import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")


# === RULE-BASED DETECTION ===
def rule_based_detection(tx):
    flagged = False
    high_conf = False
    reasons = []

    # Rule 1️⃣ — Invalid or negative amount
    if tx.get("amount", 0) <= 0:
        flagged = True
        high_conf = True
        reasons.append("Invalid amount (<=0)")

    # Rule 2️⃣ — Extremely high toll
    if tx.get("amount", 0) > 5000:
        flagged = True
        reasons.append("Abnormally high toll")

    # Rule 3️⃣ — Car being charged more than expected
    if tx.get("vehicle_type") == "CAR" and tx.get("amount", 0) > 300:
        flagged = True
        reasons.append("Car charged more than expected")

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


# === MOCK ML DETECTION ===
def mock_ml_detection(tx):
    """Mock ML detection function that simulates model predictions without requiring actual models"""
    # Generate mock probabilities based on transaction features
    base_prob = 0.1  # base probability
    
    # Increase probability if certain risk factors are present
    if tx.get("amount", 0) > 1000:
        base_prob += 0.3
    if tx.get("speed", 60) > 120:  # suspicious if going too fast
        base_prob += 0.2
    if tx.get("amount", 0) <= 0:
        base_prob += 0.5
    
    # Cap the probability
    pB = min(base_prob, 0.9)
    pA = min(base_prob * 0.8, 0.85)  # slightly different for second model
    iso_flag = 1 if base_prob > 0.5 else 0
    
    return pA, pB, iso_flag


# === COMBINED ML + RULE DETECTION ===
def run_detection(tx):
    # Step 1 — Run rule-based logic
    rule_result = rule_based_detection(tx)

    # Step 2 — Get mock ML predictions
    pA, pB, iso_flag = mock_ml_detection(tx)

    # Step 3 — Decision fusion
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