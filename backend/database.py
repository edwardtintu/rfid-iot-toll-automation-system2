# backend/database.py
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
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
    quarantine_status = Column(String(16), default="NORMAL")  # NORMAL / QUARANTINED / PROBATION
    last_violation_at = Column(DateTime, nullable=True)  # For time-decay recovery calculation
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

# ============================
#  SELF-HEALING TRUST NETWORK (Patent #1)
# ============================

# Quarantine Record — tracks when readers enter/exit quarantine
class QuarantineRecord(Base):
    __tablename__ = "quarantine_records"

    id = Column(Integer, primary_key=True, index=True)
    reader_id = Column(String(64), nullable=False, index=True)
    quarantine_reason = Column(String(64), nullable=False)  # Violation type that triggered quarantine
    severity_level = Column(Integer, default=1)  # 1-3, affects probation difficulty
    entered_at = Column(DateTime, default=datetime.utcnow)
    released_at = Column(DateTime, nullable=True)
    status = Column(String(16), default="ACTIVE")  # ACTIVE / PROBATION / RELEASED / EXPIRED
    trust_score_at_entry = Column(Integer)  # Trust score when quarantine began
    probation_started_at = Column(DateTime, nullable=True)

# Probation Challenge — test transactions a quarantined reader must pass
class ProbationChallenge(Base):
    __tablename__ = "probation_challenges"

    id = Column(Integer, primary_key=True, index=True)
    reader_id = Column(String(64), nullable=False, index=True)
    quarantine_id = Column(Integer, nullable=False)  # References quarantine_records(id)
    challenge_type = Column(String(32), nullable=False)  # KNOWN_TAG / TIMING_CHECK / SIGNATURE_VERIFY
    expected_tag_hash = Column(String(128), nullable=True)  # Known-good tag hash for verification
    challenge_data = Column(String, nullable=True)  # JSON blob with challenge parameters
    issued_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    result = Column(String(16), nullable=True)  # PASS / FAIL / TIMEOUT
    attempt_count = Column(Integer, default=0)
    max_attempts = Column(Integer, default=2)

# Peer Consensus Vote — adjacent readers vote on quarantine restoration
class PeerConsensusVote(Base):
    __tablename__ = "peer_consensus_votes"

    id = Column(Integer, primary_key=True, index=True)
    quarantine_id = Column(Integer, nullable=False, index=True)  # References quarantine_records(id)
    voter_reader_id = Column(String(64), nullable=False)  # Reader casting the vote
    vote = Column(String(8), nullable=False)  # APPROVE / REJECT
    reason = Column(String, nullable=True)  # Optional justification
    voted_at = Column(DateTime, default=datetime.utcnow)

# Tag Suspicion — elevated scrutiny on tags seen by quarantined readers
class TagSuspicion(Base):
    __tablename__ = "tag_suspicions"

    id = Column(Integer, primary_key=True, index=True)
    tag_hash = Column(String(128), nullable=False, index=True)
    source_reader_id = Column(String(64), nullable=False)  # Quarantined reader that triggered suspicion
    suspicion_multiplier = Column(Float, default=1.5)  # Fraud detection sensitivity multiplier
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)  # Auto-expire after configurable duration



# ============================
# Patent #4: VDF Chain Models
# ============================

# VDF Chain Link — each toll transaction's sequential VDF entry
class VDFChainLink(Base):
    __tablename__ = "vdf_chain_links"

    sequence_number = Column(Integer, primary_key=True)  # Sequential position in chain
    event_id = Column(String(64), nullable=False, index=True)  # References toll event
    tx_hash = Column(String(128), nullable=False)  # Transaction hash
    previous_vdf_output = Column(String(128), nullable=False)  # VDF output from link N-1
    vdf_input = Column(Text, nullable=False)  # Computed input to VDF (prev_output + tx_data)
    vdf_output = Column(String(128), nullable=False)  # Result of VDF computation
    vdf_proof = Column(Text, nullable=True)  # Proof data (JSON checkpoints)
    difficulty = Column(Integer, nullable=False)  # VDF difficulty used
    computation_time_ms = Column(Integer, nullable=True)  # Time taken for VDF computation
    created_at = Column(DateTime, default=datetime.utcnow)

# VDF Anchor — blockchain anchor checkpoints
class VDFAnchor(Base):
    __tablename__ = "vdf_anchors"

    anchor_id = Column(Integer, primary_key=True, autoincrement=True)
    start_sequence = Column(Integer, nullable=False)  # First chain link in this anchor
    end_sequence = Column(Integer, nullable=False)  # Last chain link in this anchor
    chain_hash = Column(String(128), nullable=False)  # Cumulative hash of the chain segment
    vdf_output_at_anchor = Column(String(128), nullable=False)  # VDF output at anchor point
    blockchain_tx_hash = Column(String(128), nullable=True)  # Blockchain tx hash once anchored
    anchor_status = Column(String(16), default="PENDING")  # PENDING / ANCHORED / FAILED
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(engine)
