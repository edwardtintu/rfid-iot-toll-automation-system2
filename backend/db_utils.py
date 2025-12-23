# backend/db_utils.py
from datetime import datetime
from sqlalchemy import desc
from backend.database import SessionLocal, Card, TollTariff, TollRecord

def get_card(uid: str):
    """Return (Card, session). Caller should close session if using it."""
    db = SessionLocal()
    try:
        card = db.query(Card).filter_by(tagUID=uid.upper()).first()
        return card, db
    except:
        db.close()
        raise

def get_tariff(vehicle_type: str):
    db = SessionLocal()
    try:
        t = db.query(TollTariff).filter_by(vehicle_type=vehicle_type).first()
        return (t.amount if t else 120.0)
    finally:
        db.close()

def get_last_inter_arrival(uid: str):
    db = SessionLocal()
    try:
        rec = db.query(TollRecord).filter_by(tagUID=uid.upper()).order_by(desc(TollRecord.timestamp)).first()
        if not rec:
            return 5.0  # default seconds if no history
        delta = (datetime.utcnow() - rec.timestamp).total_seconds()
        return max(delta, 0.0)
    finally:
        db.close()

def save_record(tx, result):
    db = SessionLocal()
    try:
        tr = TollRecord(
            tagUID=tx["tagUID"].upper(),
            vehicle_type=tx.get("vehicle_type", "CAR"),
            amount=tx.get("amount", 0.0),
            speed=float(tx.get("speed", 0.0)),
            decision=result["action"],
            reason=",".join(result.get("reasons", [])),
            timestamp=datetime.utcnow(),
            tx_hash=result.get("tx_hash", "")
        )
        db.add(tr)
        # update last_seen
        c = db.query(Card).filter_by(tagUID=tx["tagUID"].upper()).first()
        if c:
            c.last_seen = tr.timestamp
        db.commit()
    finally:
        db.close()

def deduct_balance(uid: str, amount: float):
    db = SessionLocal()
    try:
        c = db.query(Card).filter_by(tagUID=uid.upper()).first()
        if not c:
            return False, "card_not_registered"
        if c.balance < amount:
            return False, "low_balance"
        c.balance -= amount
        db.commit()
        return True, "deducted"
    finally:
        db.close()
