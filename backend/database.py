# backend/database.py
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# Database configuration using environment variables
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "htms")
DB_USER = os.getenv("DB_USER", "htms_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "htms_pass")

# Use environment variable for DB path, fallback to default
# If PostgreSQL environment variables are set, use PostgreSQL; otherwise use SQLite
if os.getenv("USE_POSTGRES", "false").lower() == "true":
    DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    # Ensure storage directory exists
    os.makedirs("backend/storage", exist_ok=True)
    os.makedirs("/app/storage", exist_ok=True)  # For Docker compatibility
    DB_URL = os.getenv("DATABASE_URL", "sqlite:///backend/storage/toll_data.db")

Base = declarative_base()
engine = create_engine(DB_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Card(Base):
    __tablename__ = "cards"
    id = Column(Integer, primary_key=True)
    tag_hash = Column(String, unique=True, index=True)     # Hashed RFID UID
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

class UsedNonce(Base):
    __tablename__ = "used_nonces"

    id = Column(Integer, primary_key=True, index=True)
    reader_id = Column(String, index=True)
    nonce = Column(String, index=True)
    timestamp = Column(Integer)

class Reader(Base):
    __tablename__ = "readers"

    reader_id = Column(String, primary_key=True)
    secret = Column(String)
    key_version = Column(Integer, default=1)
    status = Column(String, default="ACTIVE")  # ACTIVE / REVOKED

class TollEvent(Base):
    __tablename__ = "toll_events"

    event_id = Column(String(64), primary_key=True)
    tag_hash = Column(String(128), nullable=False)  # Changed from tag_uid_hash to tag_hash to match existing
    reader_id = Column(String(64), nullable=False)
    timestamp = Column(Integer, nullable=False)
    nonce = Column(String(64), nullable=False)
    decision = Column(String(16), nullable=False)  # ALLOWED / BLOCKED
    created_at = Column(DateTime, default=datetime.utcnow)

class BlockchainQueue(Base):
    __tablename__ = "blockchain_queue"

    queue_id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(64))  # References toll_events(event_id)
    status = Column(String(16), nullable=False, default="PENDING")  # PENDING / SYNCED / FAILED
    retry_count = Column(Integer, default=0)
    last_attempt = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# NEW: Reader Trust Table
class ReaderTrust(Base):
    __tablename__ = "reader_trust"

    id = Column(Integer, primary_key=True, index=True)
    reader_id = Column(String(64), unique=True, nullable=False)
    trust_score = Column(Integer, default=100)  # 0-100
    trust_status = Column(String(16), default="TRUSTED")  # TRUSTED / DEGRADED / SUSPENDED
    last_updated = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

# NEW: Reader Violations Table
class ReaderViolation(Base):
    __tablename__ = "reader_violations"

    id = Column(Integer, primary_key=True, index=True)
    reader_id = Column(String(64), nullable=False)
    violation_type = Column(String(64), nullable=False)  # REPLAY_ATTACK, AUTH_FAILURE, etc.
    score_delta = Column(Integer, nullable=False)  # Negative value for deduction
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(String)  # Additional details about the violation

# NEW: Decision Telemetry Table
class DecisionTelemetry(Base):
    __tablename__ = "decision_telemetry"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(64))  # References toll_events(event_id)
    reader_id = Column(String(64), nullable=False)
    trust_score = Column(Integer)  # Current trust score of the reader
    reader_status = Column(String(16))  # TRUSTED/DEGRADED/SUSPENDED
    decision = Column(String(16), nullable=False)  # allow/block
    reason = Column(String)  # Comma-separated reasons
    ml_score_a = Column(Float)  # Model A probability score
    ml_score_b = Column(Float)  # Model B probability score
    anomaly_flag = Column(Integer)  # Anomaly detection flag (0/1)
    timestamp = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(engine)
