from fastapi import FastAPI, Request
from datetime import datetime
import hashlib, json, os
from backend.detection import run_detection
from backend.blockchain import send_to_chain
from backend.database import SessionLocal, TollRecord  # <-- NEW

app = FastAPI(title="Hybrid Toll Management System")

LOG_FILE = "backend/storage/toll_logs.txt"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

@app.get("/")
def root():
    return {"message": "HTMS API running"}

@app.post("/api/toll")
async def toll_endpoint(request: Request):
    tx = await request.json()

    # Ensure required fields
    tx.setdefault("timestamp", datetime.utcnow().isoformat())
    tx.setdefault("plaza_id", "TOLL_GATE_01")
    tx.setdefault("vehicle_type", "CAR")
    tx.setdefault("amount", 120)
    tx.setdefault("speed", 60)
    tx.setdefault("inter_arrival", 5)

    # --- ML + Rule-based Detection ---
    result = run_detection(tx)

    # --- SHA256 Hash for Blockchain ---
    tx_str = json.dumps(tx, sort_keys=True)
    tx_hash = hashlib.sha256(tx_str.encode()).hexdigest()
    result["tx_hash"] = tx_hash
    result["timestamp"] = tx["timestamp"]

    # --- Save to local log file ---
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(result) + "\n")

    # --- Save to SQLite Database ---
    db = SessionLocal()
    record = TollRecord(
        tagUID=tx.get("tagUID", "UNKNOWN"),
        vehicle_type=tx.get("vehicle_type"),
        amount=tx.get("amount"),
        speed=tx.get("speed"),
        decision=result["action"],
        timestamp=datetime.utcnow(),
        tx_hash=tx_hash
    )
    db.add(record)
    db.commit()
    db.close()

    # --- Log to Blockchain ---
    send_to_chain(tx_hash, result["action"], ", ".join(result["reasons"]))

    return result
