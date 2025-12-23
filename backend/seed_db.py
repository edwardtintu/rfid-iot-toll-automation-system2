# backend/seed_db.py
from database import SessionLocal, Card, TollTariff, init_db
from datetime import datetime

def seed():
    init_db()
    db = SessionLocal()

    # ✅ 1. Add default tariffs
    tariffs = {
        "CAR": 120.0,
        "BUS": 250.0,
        "TRUCK": 400.0
    }
    for vtype, amount in tariffs.items():
        if not db.query(TollTariff).filter_by(vehicle_type=vtype).first():
            db.add(TollTariff(vehicle_type=vtype, amount=amount))
            print(f"✅ Added tariff for {vtype}: ₹{amount}")

    # ✅ 2. Add RFID Card details
    card_data = [
        {
            "tagUID": "5B88F75",
            "owner_name": "Hariharan Sundaramoorthy",
            "vehicle_number": "TN23AB1234",
            "vehicle_type": "CAR",
            "balance": 50000.0,
        },
        {
            "tagUID": "9C981B6",
            "owner_name": "Sundaramurthy",
            "vehicle_number": "TN45XY9876",
            "vehicle_type": "TRUCK",
            "balance": 1000.0,
        },
        {
            "tagUID": "BE9E1E33",
            "owner_name": "Madhu Sundaramoorthy",
            "vehicle_number": "TN10BZ2025",
            "vehicle_type": "BUS",
            "balance": 800.0,
        },
        {
            "tagUID": "A2E15F20",
            "owner_name": "Test User",
            "vehicle_number": "KA01AB1234",
            "vehicle_type": "CAR",
            "balance": 600.0,
        }
    ]

    for c in card_data:
        existing_card = db.query(Card).filter_by(tagUID=c["tagUID"]).first()
        if not existing_card:
            db.add(Card(**c))
            print(f"✅ Added card for {c['owner_name']} ({c['tagUID']})")
        else:
            # Update existing card with new values (especially balance)
            existing_card.owner_name = c["owner_name"]
            existing_card.vehicle_number = c["vehicle_number"]
            existing_card.vehicle_type = c["vehicle_type"]
            existing_card.balance = c["balance"]
            print(f"ℹ️ Card {c['tagUID']} already exists. Balance updated to ₹{c['balance']}.")

    db.commit()
    db.close()
    print("✅ Database seeding completed!")

if __name__ == "__main__":
    seed()
