#!/usr/bin/env python3
"""Seed database with experiment card data."""
import sys
import hashlib
sys.path.append("backend")

from database import SessionLocal, Card, TollTariff, Reader, ReaderTrust

db = SessionLocal()

# Add tariffs
tariffs = {"CAR": 120.0, "BUS": 250.0, "TRUCK": 400.0}
for vtype, amount in tariffs.items():
    if not db.query(TollTariff).filter_by(vehicle_type=vtype).first():
        db.add(TollTariff(vehicle_type=vtype, amount=amount))
        print(f"Added tariff: {vtype} = Rs.{amount}")

# Add the experiment card (UID: 5B88F75)
tag_uid = "5B88F75"
tag_hash = hashlib.sha256(tag_uid.encode()).hexdigest()
print(f"Card hash: {tag_hash}")

card = Card(
    tag_hash=tag_hash,
    owner_name="Experiment User",
    vehicle_number="TN23EX0001",
    vehicle_type="CAR",
    balance=5000.0
)
db.add(card)
print(f"Added card: {tag_hash[:16]}...")

# Add the experiment reader
reader = Reader(
    reader_id="RDR-001",
    secret="demo_secret",
    status="ACTIVE",
    key_version=1
)
db.add(reader)
print("Added reader: RDR-001")

# Add trust record for reader
trust = ReaderTrust(
    reader_id="RDR-001",
    trust_score=100,
    trust_status="TRUSTED"
)
db.add(trust)
print("Added trust record for RDR-001")

db.commit()
db.close()
print("Database seeded successfully!")
