# backend/database.py
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# Ensure storage directory exists
os.makedirs("backend/storage", exist_ok=True)

DB_URL = "sqlite:///backend/storage/toll_data.db"

Base = declarative_base()
engine = create_engine(DB_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Card(Base):
    __tablename__ = "cards"
    id = Column(Integer, primary_key=True)
    tagUID = Column(String, unique=True, index=True)       # RFID UID
    owner_name = Column(String, default="Unknown")
    vehicle_number = Column(String, default="NA")
    vehicle_type = Column(String, default="CAR")           # CAR/BUS/TRUCK
    balance = Column(Float, default=500.0)                 # wallet balance
    last_seen = Column(DateTime, default=None)

class TollTariff(Base):
    __tablename__ = "tariffs"
    id = Column(Integer, primary_key=True)
    vehicle_type = Column(String, index=True)              # CAR/BUS/TRUCK
    amount = Column(Float)                                 # base toll amount

class TollRecord(Base):
    __tablename__ = "toll_records"
    id = Column(Integer, primary_key=True, index=True)
    tagUID = Column(String, index=True)
    vehicle_type = Column(String)
    amount = Column(Float)
    speed = Column(Float)
    decision = Column(String)                              # allow/block
    reason = Column(String)                                # comma-joined reasons
    timestamp = Column(DateTime, default=datetime.utcnow)
    tx_hash = Column(String)

def init_db():
    Base.metadata.create_all(engine)
