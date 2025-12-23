# backend/app.py
from fastapi import FastAPI, Request, HTTPException
from datetime import datetime
import hashlib, json, os
from sqlalchemy.orm import Session

from detection_updated import run_detection
from blockchain import send_to_chain
from database import SessionLocal, Card, TollTariff, TollRecord, init_db

# === Initialize DB ===
init_db()

app = FastAPI(title="Hybrid Toll Management System")

LOG_FILE = "backend/storage/toll_logs.txt"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


@app.get("/")
def root():
    """Check if API is running."""
    return {"message": "HTMS API running"}


# ============================
#  CARD LOOKUP ENDPOINT
# ============================
@app.get("/api/card/{uid}")
def get_card(uid: str):
    """Fetch card and tariff details using RFID UID."""
    db: Session = SessionLocal()
    card = db.query(Card).filter_by(tagUID=uid.upper()).first()
    if not card:
        db.close()
        raise HTTPException(status_code=404, detail="Card not found")

    # Store card data before potentially closing session
    card_data = {
        "tagUID": card.tagUID,
        "owner_name": card.owner_name,
        "vehicle_number": card.vehicle_number,
        "vehicle_type": card.vehicle_type,
        "balance": card.balance,
        "last_seen": card.last_seen
    }
    
    tariff = db.query(TollTariff).filter_by(vehicle_type=card_data["vehicle_type"]).first()
    db.close()

    if not tariff:
        raise HTTPException(status_code=404, detail="Tariff not found")

    return {
        "uid": card_data["tagUID"],
        "owner_name": card_data["owner_name"],
        "vehicle_number": card_data["vehicle_number"],
        "vehicle_type": card_data["vehicle_type"],
        "balance": round(card_data["balance"], 2),
        "tariff_amount": tariff.amount,
        "last_seen": card_data["last_seen"].isoformat() if card_data["last_seen"] else None
    }


# ============================
#  MAIN TOLL TRANSACTION API
# ============================
@app.post("/api/toll")
async def toll_endpoint(request: Request):
    """Process RFID toll transaction."""
    tx = await request.json()
    uid = tx.get("tagUID", "").upper()

    if not uid:
        raise HTTPException(status_code=400, detail="tagUID missing")

    db: Session = SessionLocal()

    try:
        # Step 1 — Fetch card details
        card = db.query(Card).filter_by(tagUID=uid).first()
        if not card:
            raise HTTPException(status_code=404, detail=f"No record for card UID {uid}")

        # Store card data immediately to avoid detached instance errors
        card_data = {
            'tagUID': card.tagUID,
            'vehicle_type': card.vehicle_type,
            'balance': card.balance,
            'last_seen': card.last_seen
        }

        # Step 2 — Validate inputs
        speed = tx.get("speed", 60)  # Default to 60 km/h if not provided
        if speed < 0 or speed > 300:  # Validate speed is reasonable
            raise HTTPException(status_code=400, detail=f"Invalid speed: {speed} km/h. Must be between 0 and 300 km/h")

        # Step 3 — Fetch tariff
        tariff = db.query(TollTariff).filter_by(vehicle_type=card_data['vehicle_type']).first()
        if not tariff:
            raise HTTPException(status_code=404, detail=f"No tariff for type {card_data['vehicle_type']}")

        # Step 4 — Build transaction
        tx_data = {
            "tagUID": uid,
            "vehicle_type": card_data['vehicle_type'],
            "amount": tariff.amount,
            "inter_arrival": 5 , # placeholder for future time-based detection
            "last_seen": card_data['last_seen'].isoformat() if card_data['last_seen'] else None
        }

        # Step 4 — Run hybrid detection (rules + ML)
        result = run_detection(tx_data)

        # Step 5 — Generate transaction hash
        tx_str = json.dumps(tx_data, sort_keys=True)
        tx_hash = hashlib.sha256(tx_str.encode()).hexdigest()
        result["tx_hash"] = tx_hash
        result["timestamp"] = datetime.utcnow().isoformat()

        # Step 6 — Save toll record
        record = TollRecord(
            tagUID=uid,
            vehicle_type=card_data['vehicle_type'],
            amount=tariff.amount,
            speed=speed,  # Use validated speed value
            decision=result["action"],
            reason=", ".join(result["reasons"]),
            timestamp=datetime.utcnow(),
            tx_hash=tx_hash,
        )
        db.add(record)

        # Step 7 — Deduct balance if allowed
        final_balance = card_data['balance']
        if result["action"] == "allow":
            if card_data['balance'] >= tariff.amount:
                card.balance -= tariff.amount  # Update card balance in DB
                final_balance = card.balance
                result["new_balance"] = round(final_balance, 2)
            else:
                result["action"] = "block"
                result["reasons"].append("Insufficient balance")
                result["new_balance"] = round(card_data['balance'], 2)
        else:
            result["new_balance"] = round(card_data['balance'], 2)

        # Store tariff data before closing session
        tariff_amount = tariff.amount
        
        # Update last seen time
        card.last_seen = datetime.utcnow()
        db.commit()
        
    finally:
        db.close()

    # Step 8 — Log locally
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(result) + "\n")

    # Step 9 — Send to blockchain (using stored values to avoid detached instance)
    send_to_chain(
        tx_hash=tx_hash, 
        decision=result["action"], 
        reason=", ".join(result["reasons"]),
        tagUID=uid,
        vehicle_type=card_data['vehicle_type'],  # Use stored value
        amount=tariff_amount  # Use stored value
    )

    return result
