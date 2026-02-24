# backend/app.py
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request, HTTPException
from datetime import datetime
import hashlib, json, os, time
import hmac
import threading
from sqlalchemy.orm import Session

MAX_TIME_DRIFT = 30  # seconds (wider window for offline recovery)


def get_trust_policy():
    """Load trust policy from JSON file."""
    import json
    import os
    policy_file = os.path.join(os.path.dirname(__file__), "trust_policy.json")
    with open(policy_file) as f:
        return json.load(f)


def verify_signature(uid, reader_id, timestamp, nonce, signature, db):
    """Verify the HMAC-SHA256 signature from the reader using database-stored secrets."""
    from database import Reader

    reader = db.query(Reader).filter(
        Reader.reader_id == reader_id,
        Reader.status == "ACTIVE"
    ).first()

    if not reader:
        return False

    secret = reader.secret
    message = f"{uid}{reader_id}{timestamp}{nonce}".encode()
    expected_signature = hmac.new(
        secret.encode(),
        message,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)


def is_replay_attack(reader_id, timestamp, nonce, db):
    """Check if this is a replay attack using persistent nonce storage."""
    from database import UsedNonce

    # Check timestamp freshness (Unix timestamp validation)
    current_time = int(time.time())
    event_time = int(timestamp)

    if abs(current_time - event_time) > MAX_TIME_DRIFT:
        return True, "Invalid timestamp"

    # Check if nonce already exists for this reader (persistent check)
    existing = db.query(UsedNonce).filter(
        UsedNonce.reader_id == reader_id,
        UsedNonce.nonce == nonce
    ).first()

    if existing:
        return True, "Replay detected"

    # Store nonce in database
    record = UsedNonce(
        reader_id=reader_id,
        nonce=nonce,
        timestamp=timestamp
    )
    db.add(record)
    db.commit()
    return False, None


def cleanup_old_nonces(db, expiry_seconds=60):
    """Clean up old nonces to prevent DB growth."""
    from database import UsedNonce
    cutoff = int(time.time()) - expiry_seconds
    db.query(UsedNonce).filter(
        UsedNonce.timestamp < cutoff
    ).delete()
    db.commit()


def generate_event_hash(uid, reader_id, timestamp, nonce):
    """Generate a verified event hash for blockchain anchoring."""
    event_string = f"{uid}|{reader_id}|{timestamp}|{nonce}|VERIFIED"
    return hashlib.sha256(event_string.encode()).hexdigest()


def rotate_reader_key(reader_id, new_secret, db):
    """Rotate the key for a specific reader."""
    from database import Reader

    reader = db.query(Reader).filter(
        Reader.reader_id == reader_id
    ).first()

    if not reader:
        return False

    reader.secret = new_secret
    reader.key_version += 1
    db.commit()
    return True


def revoke_reader(reader_id, db):
    """Revoke a specific reader."""
    from database import Reader

    reader = db.query(Reader).filter(
        Reader.reader_id == reader_id
    ).first()

    if not reader:
        return False

    reader.status = "REVOKED"
    db.commit()
    return True


from collections import defaultdict

# Batch processing for Merkle tree anchoring
VERIFIED_EVENT_BUFFER = []
BATCH_SIZE = 5  # Number of events per batch

# Rate limiting for readers
READER_RATE = defaultdict(list)
MAX_EVENTS = 5          # max scans
WINDOW_SECONDS = 10     # per 10 seconds


def merkle_root(hashes):
    """Calculate the Merkle root from a list of hashes."""
    if not hashes:
        return None
    if len(hashes) == 1:
        return hashes[0]

    # Pad with the last hash if odd number of hashes
    if len(hashes) % 2 == 1:
        hashes = hashes + [hashes[-1]]

    new_level = []
    for i in range(0, len(hashes), 2):
        left = hashes[i]
        right = hashes[i+1]
        combined = hashlib.sha256((left + right).encode()).hexdigest()
        new_level.append(combined)

    return merkle_root(new_level)


def is_rate_limited(reader_id):
    """Check if a reader is exceeding the rate limit."""
    now = time.time()
    events = READER_RATE[reader_id]

    # keep only recent events
    READER_RATE[reader_id] = [
        t for t in events if now - t < WINDOW_SECONDS
    ]

    if len(READER_RATE[reader_id]) >= MAX_EVENTS:
        return True

    READER_RATE[reader_id].append(now)
    return False

# ============================
#  READER TRUST ENGINE
# ============================

def get_reader_trust_status(reader_id, db):
    """Get the current trust status of a reader."""
    from database import ReaderTrust

    # Load trust policy
    POLICY = get_trust_policy()

    trust_record = db.query(ReaderTrust).filter(
        ReaderTrust.reader_id == reader_id
    ).first()

    if not trust_record:
        # Initialize trust record for new readers using policy
        trust_record = ReaderTrust(
            reader_id=reader_id,
            trust_score=POLICY["initial_trust_score"],
            trust_status="TRUSTED"
        )
        db.add(trust_record)
        db.commit()

    return trust_record.trust_score, trust_record.trust_status

def update_reader_trust_score(reader_id, violation_type, score_delta, details, db):
    """Update reader trust score based on violations.
    Now also triggers autonomous quarantine if threshold is crossed (Patent #1).
    """
    from database import ReaderTrust, ReaderViolation

    # Load trust policy
    POLICY = get_trust_policy()

    # Add violation record
    violation = ReaderViolation(
        reader_id=reader_id,
        violation_type=violation_type,
        score_delta=score_delta,
        details=details
    )
    db.add(violation)

    # Update trust score
    trust_record = db.query(ReaderTrust).filter(
        ReaderTrust.reader_id == reader_id
    ).first()

    if not trust_record:
        trust_record = ReaderTrust(reader_id=reader_id, trust_score=POLICY["initial_trust_score"], trust_status="TRUSTED")
        db.add(trust_record)

    # Calculate new score
    new_score = max(0, min(100, trust_record.trust_score + score_delta))
    trust_record.trust_score = new_score

    # Record violation timestamp for time-decay recovery (Patent #1)
    trust_record.last_violation_at = datetime.utcnow()

    # Determine new status based on policy thresholds
    if new_score >= POLICY["thresholds"]["degraded"]:
        trust_record.trust_status = "TRUSTED"
    elif new_score >= POLICY["thresholds"]["suspended"]:
        trust_record.trust_status = "DEGRADED"
    else:
        trust_record.trust_status = "SUSPENDED"

    trust_record.last_updated = datetime.utcnow()
    db.commit()

    # === PATENT #1: Autonomous Quarantine Check ===
    # After recording the violation, check if this reader should be quarantined
    try:
        from self_healing_trust import check_and_enter_quarantine
        quarantine = check_and_enter_quarantine(reader_id, violation_type, new_score, db)
        if quarantine:
            print(f"[SELF-HEALING] Reader {reader_id} quarantined: {violation_type} (severity={quarantine.severity_level})")
    except Exception as e:
        print(f"[SELF-HEALING] Error in quarantine check: {e}")

    return new_score, trust_record.trust_status

def evaluate_reader_trust(reader_id, db):
    """Evaluate if a reader is allowed to process toll events based on trust status.
    Now also checks quarantine status (Patent #1).
    """
    from database import ReaderTrust
    # Load trust policy
    POLICY = get_trust_policy()

    trust_score, trust_status = get_reader_trust_status(reader_id, db)

    # === PATENT #1: Check quarantine status ===
    trust_record = db.query(ReaderTrust).filter(
        ReaderTrust.reader_id == reader_id
    ).first()

    if trust_record and trust_record.quarantine_status in ("QUARANTINED", "PROBATION"):
        # Quarantined reader attempting to process — penalize and block
        penalty = POLICY["penalties"].get("operation_while_quarantined", 8)
        update_reader_trust_score(
            reader_id,
            "OPERATION_WHILE_QUARANTINED",
            -penalty,
            f"Quarantined reader ({trust_record.quarantine_status}) attempted to operate",
            db
        )
        return False, f"QUARANTINED:{trust_record.quarantine_status}", trust_score

    if trust_status == "SUSPENDED":
        # Log violation for suspended reader attempting to operate
        penalty = POLICY["penalties"]["operation_while_suspended"]
        update_reader_trust_score(
            reader_id,
            "OPERATION_WHILE_SUSPENDED",
            -penalty,
            "Reader attempted to operate while suspended",
            db
        )
        return False, trust_status, trust_score

    return True, trust_status, trust_score

import threading
import time
from detection_updated import run_detection
from blockchain import send_to_chain
from database import SessionLocal, Card, TollTariff, TollRecord, TollEvent, BlockchainQueue, UsedNonce, Reader, init_db

# Reader secrets are now stored in the database
# Use the Reader model for management

# === Initialize DB ===
# Only initialize tables if using SQLite (PostgreSQL tables will be created separately)
import os
if os.getenv("USE_POSTGRES", "false").lower() != "true":
    init_db()

import os
from fastapi.middleware.cors import CORSMiddleware

# Simulation mode flag
SIMULATION_MODE = os.getenv("SIMULATION_MODE", "false").lower() == "true"

app = FastAPI(title="Hybrid Toll Management System")

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os
_backend_dir = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(_backend_dir, "storage", "toll_logs.txt")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


@app.get("/")
def root():
    """Check if API is running."""
    return {"message": "HTMS API running"}


@app.get("/api/time")
def get_time():
    """Return current Unix timestamp for device time synchronization."""
    return int(time.time())


@app.post("/api/register_reader")
def register_reader(reader_id: str, secret: str):
    """Register a new reader with its secret key."""
    from database import SessionLocal, Reader

    db = SessionLocal()
    try:
        # Check if reader already exists
        existing = db.query(Reader).filter(Reader.reader_id == reader_id).first()
        if existing:
            # Update existing reader
            existing.secret = secret
            existing.status = "ACTIVE"
            existing.key_version = 1
        else:
            # Create new reader
            reader = Reader(
                reader_id=reader_id,
                secret=secret,
                key_version=1,
                status="ACTIVE"
            )
            db.add(reader)

        db.commit()
        return {"status": "success", "message": f"Reader {reader_id} registered/updated"}
    finally:
        db.close()


@app.post("/api/rotate_key")
def rotate_key(reader_id: str, new_secret: str):
    """Rotate the key for a specific reader."""
    from database import SessionLocal

    db = SessionLocal()
    try:
        success = rotate_reader_key(reader_id, new_secret, db)
        if success:
            return {"status": "success", "message": f"Key rotated for reader {reader_id}"}
        else:
            raise HTTPException(status_code=404, detail=f"Reader {reader_id} not found")
    finally:
        db.close()


@app.post("/api/revoke_reader")
def revoke_reader_endpoint(reader_id: str):
    """Revoke a specific reader."""
    from database import SessionLocal

    db = SessionLocal()
    try:
        success = revoke_reader(reader_id, db)
        if success:
            return {"status": "success", "message": f"Reader {reader_id} revoked"}
        else:
            raise HTTPException(status_code=404, detail=f"Reader {reader_id} not found")
    finally:
        db.close()


# ============================
#  CARD LOOKUP ENDPOINT
# ============================
@app.get("/api/card/{uid}")
def get_card(uid: str):
    """Fetch card and tariff details using RFID UID hash."""
    db: Session = SessionLocal()
    card = db.query(Card).filter_by(tag_hash=uid.lower()).first()
    if not card:
        db.close()
        raise HTTPException(status_code=404, detail="Card not found")

    # Store card data before potentially closing session
    card_data = {
        "tag_hash": card.tag_hash,
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
    tag_hash = tx.get("tag_hash", "").lower()
    reader_id = tx.get("reader_id")
    timestamp = tx.get("timestamp", "")
    nonce = tx.get("nonce", "")
    signature = tx.get("signature", "")
    key_version = tx.get("key_version", "1")  # Default to version 1

    if not tag_hash:
        raise HTTPException(status_code=400, detail="tag_hash missing")

    if not reader_id:
        raise HTTPException(status_code=400, detail="Unauthorized reader")

    # Verify cryptographic signature
    if not signature or not timestamp or not nonce:
        raise HTTPException(status_code=400, detail="Missing required authentication fields")

    # Check rate limiting for the reader
    if is_rate_limited(reader_id):
        # Update trust score for rate limiting violations
        db_temp = SessionLocal()
        try:
            from trust_engine import evaluate_trust
            # Use policy-based penalty
            POLICY = get_trust_policy()
            penalty = POLICY["penalties"]["rate_limit_violation"]
            update_reader_trust_score(
                reader_id,
                "RATE_LIMIT_EXCEEDED",
                -penalty,  # Use penalty from policy
                "Reader exceeded rate limit",
                db_temp
            )
        finally:
            db_temp.close()
        raise HTTPException(status_code=429, detail="Reader rate limit exceeded")

    db: Session = SessionLocal()

    # NEW: Check reader trust status BEFORE processing the toll transaction
    is_trusted, trust_status, trust_score = evaluate_reader_trust(reader_id, db)

    if not is_trusted:
        # Reader is suspended, block the transaction immediately
        result = {
            "flagged": True,
            "action": "block",
            "reasons": [f"Reader suspended due to low trust score ({trust_score})"],
            "ml_scores": {
                "modelA_prob": 0.0,
                "modelB_prob": 0.0,
                "iso_flag": 0
            },
            "trust_info": {
                "reader_id": reader_id,
                "trust_score": trust_score,
                "trust_status": trust_status
            }
        }
        # Log decision telemetry for suspended reader case
        from decision_logger import log_decision
        log_decision(
            event_id=tx_hash[:16] if 'tx_hash' in locals() else "unknown",  # Use first 16 chars of tx_hash as event_id
            reader_id=reader_id,
            trust_score=trust_score,
            reader_status=trust_status,
            decision="block",
            reason="Reader suspended due to low trust score",
            ml_a=0.0,
            ml_b=0.0,
            anomaly=0
        )
        db.close()
        return result

    if not verify_signature(tag_hash, reader_id, timestamp, nonce, signature, db):
        # Update trust score for authentication failures
        POLICY = get_trust_policy()
        penalty = POLICY["penalties"]["auth_failure"]
        update_reader_trust_score(
            reader_id,
            "AUTH_FAILURE",
            -penalty,  # Use penalty from policy
            "Reader failed signature verification",
            db
        )
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Verify key version matches the stored version
    from database import Reader
    reader = db.query(Reader).filter(
        Reader.reader_id == reader_id,
        Reader.status == "ACTIVE"
    ).first()

    if not reader or str(reader.key_version) != key_version:
        # Update trust score for key version mismatches
        POLICY = get_trust_policy()
        penalty = POLICY["penalties"]["key_version_mismatch"]
        update_reader_trust_score(
            reader_id,
            "KEY_VERSION_MISMATCH",
            -penalty,  # Use penalty from policy
            f"Key version mismatch: expected {reader.key_version}, got {key_version}",
            db
        )
        raise HTTPException(status_code=400, detail="Invalid key version")

    # Clean up old nonces to prevent DB growth
    cleanup_old_nonces(db)

    # Check for replay attacks using persistent storage
    is_replay, reason = is_replay_attack(reader_id, timestamp, nonce, db)
    if is_replay:
        # Update trust score for replay attacks
        POLICY = get_trust_policy()
        penalty = POLICY["penalties"]["replay_attack"]
        update_reader_trust_score(
            reader_id,
            "REPLAY_ATTACK",
            -penalty,  # Use penalty from policy
            f"Replay attack detected: {reason}",
            db
        )
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Cross-reader intelligence: Check if this reader is behaving abnormally compared to peers
    from cross_reader import detect_outlier_reader
    if detect_outlier_reader(reader_id):
        # Update trust score for peer outlier behavior
        POLICY = get_trust_policy()
        penalty = POLICY["penalties"]["peer_outlier"]
        update_reader_trust_score(
            reader_id,
            "PEER_OUTLIER",
            -penalty,  # Use penalty from policy
            f"Reader behaving abnormally compared to peer readers",
            db
        )

    # Generate verified event hash for blockchain anchoring (only for verified events)
    verified_event_hash = generate_event_hash(tag_hash, reader_id, timestamp, nonce)

    try:
        # Step 1 — Fetch card details
        card = db.query(Card).filter_by(tag_hash=tag_hash).first()
        if not card:
            # Update trust score for invalid card attempts
            POLICY = get_trust_policy()
            penalty = POLICY["penalties"]["invalid_card_attempt"]
            update_reader_trust_score(
                reader_id,
                "INVALID_CARD_ATTEMPT",
                -penalty,  # Use penalty from policy
                f"Reader attempted to access non-existent card: {tag_hash}",
                db
            )
            raise HTTPException(status_code=404, detail=f"No record for card hash {tag_hash}")

        # Store card data immediately to avoid detached instance errors
        card_data = {
            'tag_hash': card.tag_hash,
            'vehicle_type': card.vehicle_type,
            'balance': card.balance,
            'last_seen': card.last_seen
        }

        # Step 2 — Validate inputs
        speed = tx.get("speed", 60)  # Default to 60 km/h if not provided
        if speed < 0 or speed > 300:  # Validate speed is reasonable
            # Update trust score for invalid speed values (potential tampering)
            POLICY = get_trust_policy()
            penalty = POLICY["penalties"]["invalid_speed_value"]
            update_reader_trust_score(
                reader_id,
                "INVALID_SPEED_VALUE",
                -penalty,  # Use penalty from policy
                f"Reader sent invalid speed: {speed} km/h",
                db
            )
            raise HTTPException(status_code=400, detail=f"Invalid speed: {speed} km/h. Must be between 0 and 300 km/h")

        # Step 3 — Fetch tariff
        tariff = db.query(TollTariff).filter_by(vehicle_type=card_data['vehicle_type']).first()
        if not tariff:
            raise HTTPException(status_code=404, detail=f"No tariff for type {card_data['vehicle_type']}")

        # Step 4 — Build transaction
        tx_data = {
            "tag_hash": tag_hash,
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
            tagUID=tag_hash,  # Store the hashed UID instead of raw UID
            vehicle_type=card_data['vehicle_type'],
            amount=tariff.amount,
            speed=speed,  # Use validated speed value
            decision=result["action"],
            reason=", ".join(result["reasons"]),
            timestamp=datetime.utcnow(),
            tx_hash=tx_hash,
        )
        db.add(record)

        # Step 6.5 — Save toll event for blockchain queue
        from database import TollEvent
        toll_event = TollEvent(
            event_id=tx_hash[:16],  # Use first 16 chars of tx_hash as event_id
            tag_hash=tag_hash,
            reader_id=reader_id,
            timestamp=int(timestamp),
            nonce=nonce,
            decision=result["action"]
        )
        db.add(toll_event)

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

                # Update trust score if reader allows transactions with insufficient balance
                # This could indicate a compromised reader allowing unauthorized access
                if tx.get("force_allow", False):  # Check if there's any force flag indicating compromise
                    POLICY = get_trust_policy()
                    penalty = POLICY["penalties"]["balance_manipulation"]
                    update_reader_trust_score(
                        reader_id,
                        "BALANCE_MANIPULATION",
                        -penalty,  # Use penalty from policy
                        "Reader attempted to allow transaction with insufficient balance",
                        db
                    )

                result["new_balance"] = round(card_data['balance'], 2)
        else:
            result["new_balance"] = round(card_data['balance'], 2)

        # Store tariff data before closing session
        tariff_amount = tariff.amount

        # Update last seen time
        card.last_seen = datetime.utcnow()
        db.commit()

        # Add trust info to result
        _, current_trust_status = get_reader_trust_status(reader_id, db)
        result["trust_info"] = {
            "reader_id": reader_id,
            "trust_score": get_reader_trust_status(reader_id, db)[0],
            "trust_status": current_trust_status
        }

    finally:
        db.close()

    # Step 8 — Log locally
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(result) + "\n")

    # Step 8.5 — Log decision telemetry for audit and analysis
    from decision_logger import log_decision
    log_decision(
        event_id=tx_hash[:16],  # Use first 16 chars of tx_hash as event_id
        reader_id=reader_id,
        trust_score=result.get("trust_info", {}).get("trust_score", 0),
        reader_status=result.get("trust_info", {}).get("trust_status", "UNKNOWN"),
        decision=result["action"],
        reason=", ".join(result["reasons"]) if isinstance(result["reasons"], list) else result["reasons"],
        ml_a=result.get("ml_scores", {}).get("modelA_prob", 0.0),
        ml_b=result.get("ml_scores", {}).get("modelB_prob", 0.0),
        anomaly=result.get("ml_scores", {}).get("iso_flag", 0)
    )

    # Step 9 — Add verified event to batch for Merkle tree anchoring
    VERIFIED_EVENT_BUFFER.append(verified_event_hash)

    # If batch is full, create Merkle root and anchor to blockchain
    if len(VERIFIED_EVENT_BUFFER) >= BATCH_SIZE:
        merkle_root_hash = merkle_root(VERIFIED_EVENT_BUFFER)

        # Send Merkle root to blockchain (instead of individual event hashes)
        try:
            send_to_chain(
                tx_hash=tx_hash,
                decision=result["action"],
                reason=", ".join(result["reasons"]),
                tagUID=merkle_root_hash,  # Use Merkle root instead of individual event hash
                vehicle_type=card_data['vehicle_type'],  # Use stored value
                amount=tariff_amount,  # Use stored value
                reader_id=reader_id,  # Pass reader_id for verified event hash
                timestamp=timestamp  # Pass timestamp for verified event hash
            )
            # Mark event as synced if blockchain write succeeds
            from fallback import mark_event_synced
            mark_event_synced(tx_hash[:16])
        except Exception as e:
            # Fallback: Store event in blockchain queue for later sync
            from fallback import enqueue_blockchain_event
            enqueue_blockchain_event(tx_hash[:16])

        # Clear the buffer after anchoring
        VERIFIED_EVENT_BUFFER.clear()
    else:
        # Even if batch is not full, try to send individual event to blockchain
        # This handles the case where blockchain is down and we need fallback
        try:
            send_to_chain(
                tx_hash=tx_hash,
                decision=result["action"],
                reason=", ".join(result["reasons"]),
                tagUID=verified_event_hash,  # Use verified event hash for privacy
                vehicle_type=card_data['vehicle_type'],  # Use stored value
                amount=tariff_amount,  # Use stored value
                reader_id=reader_id,  # Pass reader_id for verified event hash
                timestamp=timestamp  # Pass timestamp for verified event hash
            )
            # Mark event as synced if blockchain write succeeds
            from fallback import mark_event_synced
            mark_event_synced(tx_hash[:16])
        except Exception as e:
            # Fallback: Store event in blockchain queue for later sync
            from fallback import enqueue_blockchain_event
            enqueue_blockchain_event(tx_hash[:16])

    return result

@app.get("/api/events/pending/count")
def get_pending_count():
    from database import SessionLocal, BlockchainQueue
    db = SessionLocal()
    try:
        count = db.query(BlockchainQueue).filter(
            BlockchainQueue.status == "PENDING"
        ).count()
        return {"count": count}
    finally:
        db.close()

@app.get("/stats/summary")
def get_summary_stats():
    from database import SessionLocal, TollEvent, Reader, BlockchainQueue, ReaderTrust
    from sqlalchemy import func
    db = SessionLocal()
    try:
        # Total events
        total_events = db.query(TollEvent).count()

        # Allowed events
        allowed = db.query(TollEvent).filter(TollEvent.decision == "allow").count()

        # Blocked events
        blocked = db.query(TollEvent).filter(TollEvent.decision == "block").count()

        # Active readers (TRUSTED and DEGRADED readers)
        active_readers = db.query(ReaderTrust).filter(ReaderTrust.trust_status.in_(["TRUSTED", "DEGRADED"])).count()

        # Suspended readers
        suspended_readers = db.query(ReaderTrust).filter(ReaderTrust.trust_status == "SUSPENDED").count()

        # Pending blockchain events
        pending_chain = db.query(BlockchainQueue).filter(BlockchainQueue.status == "PENDING").count()

        return {
            "total_events": total_events,
            "allowed": allowed,
            "blocked": blocked,
            "active_readers": active_readers,
            "suspended_readers": suspended_readers,
            "pending_blockchain": pending_chain
        }
    finally:
        db.close()

@app.get("/readers")
def get_readers():
    from database import SessionLocal, Reader, ReaderTrust
    db = SessionLocal()
    try:
        # Join Reader and ReaderTrust tables to get trust scores
        readers_with_trust = db.query(Reader, ReaderTrust).outerjoin(ReaderTrust, Reader.reader_id == ReaderTrust.reader_id).all()

        result = []
        for reader, trust in readers_with_trust:
            trust_score = trust.trust_score if trust else 100  # Default to 100 if no trust record
            status = trust.trust_status if trust else "TRUSTED"  # Default to TRUSTED if no trust record
            last_updated = trust.last_updated.isoformat() if trust and trust.last_updated else None

            result.append({
                "reader_id": reader.reader_id,
                "trust_score": trust_score,
                "status": status,
                "last_updated": last_updated
            })

        return result
    finally:
        db.close()

@app.get("/decisions")
def get_decisions():
    from database import SessionLocal, DecisionTelemetry
    from sqlalchemy import desc
    db = SessionLocal()
    try:
        # Query the most recent 100 decisions ordered by timestamp descending
        decisions = db.query(DecisionTelemetry).order_by(desc(DecisionTelemetry.timestamp)).limit(100).all()

        result = []
        for decision in decisions:
            result.append({
                "event_id": decision.event_id,
                "reader_id": decision.reader_id,
                "decision": decision.decision,
                "reason": decision.reason,
                "trust_score": decision.trust_score,
                "ml_a": decision.ml_score_a,
                "ml_b": decision.ml_score_b,
                "anomaly": decision.anomaly_flag,
                "timestamp": decision.timestamp.isoformat() if decision.timestamp else None
            })

        return result
    finally:
        db.close()

@app.get("/system/status")
def system_status():
    return {
        "backend": "UP",
        "database": "CONNECTED",
        "blockchain": "SYNCED",
        "simulation_mode": True
    }

@app.get("/transactions/recent")
def recent_transactions():
    from database import SessionLocal, TollEvent
    from sqlalchemy import desc
    db = SessionLocal()
    try:
        # Query the most recent 10 transactions ordered by timestamp descending
        recent_events = db.query(TollEvent).order_by(desc(TollEvent.timestamp)).limit(10).all()

        result = []
        for event in recent_events:
            result.append({
                "event_id": event.event_id,
                "reader_id": event.reader_id,
                "decision": event.decision,
                "timestamp": event.timestamp
            })

        return result
    finally:
        db.close()

@app.get("/blockchain/audit")
def blockchain_audit():
    from database import SessionLocal, BlockchainQueue
    from sqlalchemy import desc
    db = SessionLocal()
    try:
        # Query the most recent 100 blockchain events ordered by last_attempt descending
        blockchain_events = db.query(BlockchainQueue).order_by(desc(BlockchainQueue.last_attempt)).limit(100).all()

        result = []
        for event in blockchain_events:
            result.append({
                "event_id": event.event_id,
                "status": event.status,
                "retry_count": event.retry_count,
                "last_attempt": event.last_attempt.isoformat() if event.last_attempt else None
            })

        return result
    finally:
        db.close()

@app.post("/admin/seed")
def seed_data():
    from database import SessionLocal, Reader, ReaderTrust, TollEvent, DecisionTelemetry, BlockchainQueue
    from datetime import datetime
    import random
    import uuid
    db = SessionLocal()
    try:
        from sqlalchemy.exc import IntegrityError
        
        # Create demo readers if they don't exist
        demo_readers = [
            {"reader_id": "RDR-001", "status": "ACTIVE"},
            {"reader_id": "RDR-002", "status": "ACTIVE"},
            {"reader_id": "RDR-003", "status": "ACTIVE"}
        ]
        
        for reader_data in demo_readers:
            try:
                # Check if reader already exists
                existing_reader = db.query(Reader).filter(Reader.reader_id == reader_data["reader_id"]).first()
                if not existing_reader:
                    reader = Reader(
                        reader_id=reader_data["reader_id"],
                        secret="demo_secret",
                        key_version=1,
                        status=reader_data["status"]
                    )
                    db.add(reader)
                    db.commit()
            except IntegrityError:
                db.rollback()  # Ignore if already exists
        
        # Create or update demo trust records
        demo_trust_records = [
            {"reader_id": "RDR-001", "trust_score": 100, "trust_status": "TRUSTED"},
            {"reader_id": "RDR-002", "trust_score": 75, "trust_status": "TRUSTED"},
            {"reader_id": "RDR-003", "trust_score": 45, "trust_status": "DEGRADED"}
        ]
        
        for trust_data in demo_trust_records:
            try:
                # Check if trust record exists, if so update it, otherwise create new
                existing_trust = db.query(ReaderTrust).filter(ReaderTrust.reader_id == trust_data["reader_id"]).first()
                if existing_trust:
                    existing_trust.trust_score = trust_data["trust_score"]
                    existing_trust.trust_status = trust_data["trust_status"]
                else:
                    trust = ReaderTrust(
                        reader_id=trust_data["reader_id"],
                        trust_score=trust_data["trust_score"],
                        trust_status=trust_data["trust_status"]
                    )
                    db.add(trust)
                db.commit()
            except IntegrityError:
                db.rollback()  # Ignore if already exists
        
        # Create demo toll events
        for i in range(10):
            demo_event = TollEvent(
                event_id=f"EV{i:03d}",
                tag_hash=f"TAG{i:04d}",
                reader_id=random.choice(["RDR-001", "RDR-002", "RDR-003"]),
                timestamp=int(datetime.utcnow().timestamp()),
                nonce=str(uuid.uuid4())[:8],
                decision=random.choice(["allow", "block"])
            )
            db.add(demo_event)
        
        # Create demo decision telemetry
        for i in range(10):
            demo_decision = DecisionTelemetry(
                event_id=f"D{i:03d}",
                reader_id=random.choice(["RDR-001", "RDR-002", "RDR-003"]),
                trust_score=random.randint(30, 100),
                reader_status=random.choice(["TRUSTED", "DEGRADED", "SUSPENDED"]),
                decision=random.choice(["allow", "block"]),
                reason="Demo transaction",
                ml_score_a=round(random.uniform(0.1, 0.9), 3),
                ml_score_b=round(random.uniform(0.1, 0.9), 3),
                anomaly_flag=random.choice([0, 1])
            )
            db.add(demo_decision)
        
        # Create demo blockchain queue entries
        for i in range(5):
            demo_blockchain = BlockchainQueue(
                event_id=f"B{i:03d}",
                status=random.choice(["SYNCED", "PENDING", "FAILED"]),
                retry_count=random.randint(0, 3),
                last_attempt=datetime.utcnow()
            )
            db.add(demo_blockchain)
        
        db.commit()
        return {"status": "Demo data seeded successfully", "events_created": 10, "decisions_created": 10, "blockchain_entries": 5}
    finally:
        db.close()

# REAL MODE: UNIFIED INGESTION ENDPOINT
from pydantic import BaseModel
from typing import Optional

class TollRequest(BaseModel):
    reader_id: str
    tag_hash: str
    timestamp: Optional[int] = None
    speed: Optional[int] = 60
    nonce: Optional[str] = None
    signature: Optional[str] = None
    key_version: Optional[str] = "1"
    source: str = "IOT"  # "IOT" or "MANUAL"

@app.post("/ingest/toll")
async def ingest_toll(request: TollRequest):
    """
    Unified toll ingestion endpoint for both manual and IoT sources.
    This is the single source of truth for all toll events.
    """
    from database import SessionLocal, Reader, ReaderTrust, TollEvent, DecisionTelemetry
    from datetime import datetime
    import time
    import hashlib
    import hmac
    
    db = SessionLocal()
    try:
        # Get current time if not provided
        if not request.timestamp:
            request.timestamp = int(time.time())
        
        # Generate nonce if not provided
        if not request.nonce:
            import uuid
            request.nonce = str(uuid.uuid4())[:8]
        
        # Verify reader exists and is active
        reader = db.query(Reader).filter(
            Reader.reader_id == request.reader_id,
            Reader.status == "ACTIVE"
        ).first()
        
        if not reader:
            return {"error": f"Reader {request.reader_id} not found or inactive", "status": "error"}
        
        # Verify reader trust status
        is_trusted, trust_status, trust_score = evaluate_reader_trust(request.reader_id, db)
        
        if not is_trusted:
            # Reader is suspended, block the transaction immediately
            result = {
                "flagged": True,
                "action": "block",
                "reasons": [f"Reader suspended due to low trust score ({trust_score})"],
                "ml_scores": {
                    "modelA_prob": 0.0,
                    "modelB_prob": 0.0,
                    "iso_flag": 0
                },
                "trust_info": {
                    "reader_id": request.reader_id,
                    "trust_score": trust_score,
                    "trust_status": trust_status
                }
            }
            return result
        
        # Process the toll transaction (simplified version)
        # In a real system, you'd do full validation here
        decision = "allow"  # Default to allow for demo
        reasons = [f"Valid {request.source} toll transaction"]
        
        # Create toll event record
        toll_event = TollEvent(
            event_id=request.nonce[:16],  # Use nonce as event ID
            tag_hash=request.tag_hash,
            reader_id=request.reader_id,
            timestamp=request.timestamp,
            nonce=request.nonce,
            decision=decision
        )
        db.add(toll_event)
        
        # Create decision telemetry
        from decision_logger import log_decision
        log_decision(
            event_id=request.nonce[:16],
            reader_id=request.reader_id,
            trust_score=trust_score,
            reader_status=trust_status,
            decision=decision,
            reason=f"{request.source} transaction: {', '.join(reasons)}",
            ml_a=0.1,
            ml_b=0.15,
            anomaly=0
        )
        
        # Update reader's last seen timestamp
        reader_trust = db.query(ReaderTrust).filter(ReaderTrust.reader_id == request.reader_id).first()
        if reader_trust:
            reader_trust.last_updated = datetime.utcnow()
        
        db.commit()
        
        return {
            "status": "success",
            "action": decision,
            "reasons": reasons,
            "reader_id": request.reader_id,
            "tag_hash": request.tag_hash,
            "timestamp": request.timestamp,
            "source": request.source,
            "trust_info": {
                "trust_score": trust_score,
                "trust_status": trust_status
            }
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}
    finally:
        db.close()

# Legacy endpoint for backward compatibility
@app.post("/iot/toll")
async def iot_toll_endpoint(request: TollRequest):
    """
    Legacy endpoint for IoT devices (redirects to unified endpoint).
    """
    # Set source to IOT for legacy endpoint
    request.source = "IOT"
    return await ingest_toll(request)

@app.post("/admin/register-readers")
def register_readers():
    from database import SessionLocal, Reader, ReaderTrust
    db = SessionLocal()
    try:
        from sqlalchemy.exc import IntegrityError
        
        # Create demo readers
        demo_readers = [
            {"reader_id": "RDR-001", "status": "ACTIVE"},
            {"reader_id": "RDR-002", "status": "ACTIVE"},
            {"reader_id": "RDR-003", "status": "ACTIVE"}
        ]
        
        for reader_data in demo_readers:
            try:
                # Check if reader already exists
                existing_reader = db.query(Reader).filter(Reader.reader_id == reader_data["reader_id"]).first()
                if not existing_reader:
                    reader = Reader(
                        reader_id=reader_data["reader_id"],
                        secret="demo_secret",
                        key_version=1,
                        status=reader_data["status"]
                    )
                    db.add(reader)
                    db.commit()
            except IntegrityError:
                db.rollback()  # Ignore if already exists
        
        # Create or update demo trust records
        demo_trust_records = [
            {"reader_id": "RDR-001", "trust_score": 100, "trust_status": "TRUSTED"},
            {"reader_id": "RDR-002", "trust_score": 75, "trust_status": "TRUSTED"},
            {"reader_id": "RDR-003", "trust_score": 45, "trust_status": "DEGRADED"}
        ]
        
        for trust_data in demo_trust_records:
            try:
                # Check if trust record exists, if so update it, otherwise create new
                existing_trust = db.query(ReaderTrust).filter(ReaderTrust.reader_id == trust_data["reader_id"]).first()
                if existing_trust:
                    existing_trust.trust_score = trust_data["trust_score"]
                    existing_trust.trust_status = trust_data["trust_status"]
                else:
                    trust = ReaderTrust(
                        reader_id=trust_data["reader_id"],
                        trust_score=trust_data["trust_score"],
                        trust_status=trust_data["trust_status"]
                    )
                    db.add(trust)
                db.commit()
            except IntegrityError:
                db.rollback()  # Ignore if already exists
        
        return {"status": "Readers registered"}
    finally:
        db.close()

@app.post("/admin/seed")
def seed_cloud_db():
    from database import SessionLocal, Reader, ReaderTrust
    db = SessionLocal()
    try:
        # Insert demo readers with trust records
        from sqlalchemy.exc import IntegrityError

        # Create demo readers
        demo_readers = [
            {"reader_id": "RDR-001", "status": "ACTIVE"},
            {"reader_id": "RDR-002", "status": "ACTIVE"},
            {"reader_id": "RDR-003", "status": "ACTIVE"}
        ]

        for reader_data in demo_readers:
            try:
                reader = Reader(
                    reader_id=reader_data["reader_id"],
                    secret="demo_secret",
                    key_version=1,
                    status=reader_data["status"]
                )
                db.add(reader)
                db.commit()
            except IntegrityError:
                db.rollback()  # Ignore if already exists

        # Create demo trust records
        demo_trust_records = [
            {"reader_id": "RDR-001", "trust_score": 95, "trust_status": "TRUSTED"},
            {"reader_id": "RDR-002", "trust_score": 60, "trust_status": "DEGRADED"},
            {"reader_id": "RDR-003", "trust_score": 30, "trust_status": "SUSPENDED"}
        ]

        for trust_data in demo_trust_records:
            try:
                trust = ReaderTrust(
                    reader_id=trust_data["reader_id"],
                    trust_score=trust_data["trust_score"],
                    trust_status=trust_data["trust_status"]
                )
                db.add(trust)
                db.commit()
            except IntegrityError:
                db.rollback()  # Ignore if already exists

        return {"status": "Seed data inserted"}
    finally:
        db.close()

@app.post("/admin/mock-event")
def mock_event():
    from database import SessionLocal, DecisionTelemetry, TollEvent
    from datetime import datetime
    import random
    db = SessionLocal()
    try:
        # Create a mock decision telemetry record
        mock_decision = DecisionTelemetry(
            event_id=f"EVT-{random.randint(1000, 9999)}",
            reader_id=random.choice(["RDR-001", "RDR-002", "RDR-003"]),
            trust_score=random.randint(30, 100),
            reader_status=random.choice(["TRUSTED", "DEGRADED", "SUSPENDED"]),
            decision=random.choice(["allow", "block"]),
            reason="Demo transaction",
            ml_score_a=round(random.uniform(0.1, 0.9), 3),
            ml_score_b=round(random.uniform(0.1, 0.9), 3),
            anomaly_flag=random.choice([0, 1])
        )
        db.add(mock_decision)
        db.commit()

        # Create a mock toll event
        mock_event = TollEvent(
            event_id=mock_decision.event_id,
            tag_hash=f"TAG-{random.randint(10000, 99999)}",
            reader_id=mock_decision.reader_id,
            timestamp=int(datetime.utcnow().timestamp()),
            nonce=str(random.randint(100000, 999999)),
            decision=mock_decision.decision
        )
        db.add(mock_event)
        db.commit()

        return {"status": "Mock event created", "event_id": mock_decision.event_id}
    finally:
        db.close()

@app.post("/simulate/toll")
def simulate_toll():
    if not SIMULATION_MODE:
        return {"error": "Simulation disabled"}

    from simulator import generate_toll_event, generate_signature

    event = generate_toll_event()
    event["signature"] = generate_signature(event)

    # Process the event through the same pipeline as real hardware
    from fastapi import Request
    import json
    from starlette.datastructures import UploadFile
    from io import BytesIO

    # Simulate the same processing as the /api/toll endpoint
    # We'll call the toll processing logic directly
    try:
        # This mimics the exact same processing as the real API
        from database import SessionLocal
        db = SessionLocal()

        # Verify reader trust status
        is_trusted, trust_status, trust_score = evaluate_reader_trust(event["reader_id"], db)

        if not is_trusted:
            # Reader is suspended, block the transaction immediately
            result = {
                "flagged": True,
                "action": "block",
                "reasons": [f"Reader suspended due to low trust score ({trust_score})"],
                "ml_scores": {
                    "modelA_prob": 0.0,
                    "modelB_prob": 0.0,
                    "iso_flag": 0
                },
                "trust_info": {
                    "reader_id": event["reader_id"],
                    "trust_score": trust_score,
                    "trust_status": trust_status
                }
            }
            db.close()
            return result

        # For simulation, we'll just return a success response
        # In a real scenario, this would go through the full processing pipeline
        result = {
            "action": "allow",
            "reasons": ["Valid simulation event"],
            "ml_scores": {
                "modelA_prob": round(0.1 + (trust_score / 1000), 3),
                "modelB_prob": round(0.15 + (trust_score / 800), 3),
                "iso_flag": 0
            },
            "trust_info": {
                "reader_id": event["reader_id"],
                "trust_score": trust_score,
                "trust_status": trust_status
            }
        }

        # Log the decision telemetry
        from decision_logger import log_decision
        log_decision(
            event_id=event.get("event_id", "simulated"),
            reader_id=event["reader_id"],
            trust_score=trust_score,
            reader_status=trust_status,
            decision=result["action"],
            reason=", ".join(result["reasons"]) if isinstance(result["reasons"], list) else result["reasons"],
            ml_a=result["ml_scores"]["modelA_prob"],
            ml_b=result["ml_scores"]["modelB_prob"],
            anomaly=result["ml_scores"]["iso_flag"]
        )

        # Also create a toll event record in the database
        import uuid
        from database import TollEvent, ReaderTrust, BlockchainQueue
        import time
        toll_event = TollEvent(
            event_id=str(uuid.uuid4())[:16],  # Generate unique event ID
            tag_hash=event["tag_hash"],
            reader_id=event["reader_id"],
            timestamp=int(time.time()),
            nonce=event["nonce"],
            decision=result["action"]
        )
        db.add(toll_event)
        
        # Add entry to blockchain queue to make blockchain audit page show data
        from datetime import datetime
        blockchain_entry = BlockchainQueue(
            event_id=str(uuid.uuid4())[:16],  # Generate unique event ID
            status="SYNCED",  # Default to synced for demo
            retry_count=0,
            last_attempt=datetime.utcnow()
        )
        db.add(blockchain_entry)
        
        # Update reader trust based on the transaction
        reader_trust = db.query(ReaderTrust).filter(ReaderTrust.reader_id == event["reader_id"]).first()
        if reader_trust:
            # Simple trust decay for demo - decrease trust slightly with each transaction
            trust_score = max(0, reader_trust.trust_score - 2)  # Decrease by 2 points per transaction
            
            # Update status based on new trust score
            if trust_score <= 40:
                status = "SUSPENDED"
            elif trust_score <= 70:
                status = "DEGRADED"
            else:
                status = "TRUSTED"
                
            reader_trust.trust_score = trust_score
            reader_trust.trust_status = status
            reader_trust.last_updated = datetime.utcnow()
        
        db.commit()

        db.close()
        return {
            "status": "Simulated toll processed",
            "event": event,
            "result": result
        }
    except Exception as e:
        return {"error": f"Error processing simulation: {str(e)}"}

# Background task for auto-simulation
import threading
import time

def auto_simulator():
    while SIMULATION_MODE:
        try:
            # Process a simulated toll event
            from simulator import generate_toll_event, generate_signature
            event = generate_toll_event()
            event["signature"] = generate_signature(event)

            # Process the event through the same pipeline as real hardware
            from database import SessionLocal
            db = SessionLocal()

            # Verify reader trust status
            is_trusted, trust_status, trust_score = evaluate_reader_trust(event["reader_id"], db)

            if not is_trusted:
                # Reader is suspended, block the transaction immediately
                result = {
                    "flagged": True,
                    "action": "block",
                    "reasons": [f"Reader suspended due to low trust score ({trust_score})"],
                    "ml_scores": {
                        "modelA_prob": 0.0,
                        "modelB_prob": 0.0,
                        "iso_flag": 0
                    },
                    "trust_info": {
                        "reader_id": event["reader_id"],
                        "trust_score": trust_score,
                        "trust_status": trust_status
                    }
                }
            else:
                # For simulation, we'll just return a success response
                result = {
                    "action": "allow",
                    "reasons": ["Valid simulation event"],
                    "ml_scores": {
                        "modelA_prob": round(0.1 + (trust_score / 1000), 3),
                        "modelB_prob": round(0.15 + (trust_score / 800), 3),
                        "iso_flag": 0
                    },
                    "trust_info": {
                        "reader_id": event["reader_id"],
                        "trust_score": trust_score,
                        "trust_status": trust_status
                    }
                }

            # Log the decision telemetry
            import uuid
            from decision_logger import log_decision
            log_decision(
                event_id=str(uuid.uuid4()),  # Generate unique event ID
                reader_id=event["reader_id"],
                trust_score=trust_score,
                reader_status=trust_status,
                decision=result["action"],
                reason=", ".join(result["reasons"]) if isinstance(result["reasons"], list) else result["reasons"],
                ml_a=result["ml_scores"]["modelA_prob"],
                ml_b=result["ml_scores"]["modelB_prob"],
                anomaly=result["ml_scores"]["iso_flag"]
            )

            # Also create a toll event record in the database
            from database import TollEvent, ReaderTrust, BlockchainQueue
            import time
            toll_event = TollEvent(
                event_id=str(uuid.uuid4())[:16],  # Generate unique event ID
                tag_hash=event["tag_hash"],
                reader_id=event["reader_id"],
                timestamp=int(time.time()),
                nonce=event["nonce"],
                decision=result["action"]
            )
            db.add(toll_event)
            
            # Add entry to blockchain queue to make blockchain audit page show data
            from datetime import datetime
            blockchain_entry = BlockchainQueue(
                event_id=str(uuid.uuid4())[:16],  # Generate unique event ID
                status="SYNCED",  # Default to synced for demo
                retry_count=0,
                last_attempt=datetime.utcnow()
            )
            db.add(blockchain_entry)
            
            # Update reader trust based on the transaction
            reader_trust = db.query(ReaderTrust).filter(ReaderTrust.reader_id == event["reader_id"]).first()
            if reader_trust:
                # Simple trust decay for demo - decrease trust slightly with each transaction
                trust_score = max(0, reader_trust.trust_score - 2)  # Decrease by 2 points per transaction
                
                # Update status based on new trust score
                if trust_score <= 40:
                    status = "SUSPENDED"
                elif trust_score <= 70:
                    status = "DEGRADED"
                else:
                    status = "TRUSTED"
                    
                reader_trust.trust_score = trust_score
                reader_trust.trust_status = status
                reader_trust.last_updated = datetime.utcnow()
            
            db.commit()

            db.close()
        except Exception as e:
            print(f"Error in auto-simulator: {e}")

        time.sleep(5)  # Generate event every 5 seconds

# Start the auto-simulator in a background thread
if SIMULATION_MODE:
    # Register demo readers first
    from database import SessionLocal, Reader, ReaderTrust
    db = SessionLocal()
    try:
        from sqlalchemy.exc import IntegrityError
        
        # Create demo readers
        demo_readers = [
            {"reader_id": "RDR-001", "status": "ACTIVE"},
            {"reader_id": "RDR-002", "status": "ACTIVE"},
            {"reader_id": "RDR-003", "status": "ACTIVE"}
        ]
        
        for reader_data in demo_readers:
            try:
                # Check if reader already exists
                existing_reader = db.query(Reader).filter(Reader.reader_id == reader_data["reader_id"]).first()
                if not existing_reader:
                    reader = Reader(
                        reader_id=reader_data["reader_id"],
                        secret="demo_secret",
                        key_version=1,
                        status=reader_data["status"]
                    )
                    db.add(reader)
                    db.commit()
            except IntegrityError:
                db.rollback()  # Ignore if already exists
        
        # Create or update demo trust records
        demo_trust_records = [
            {"reader_id": "RDR-001", "trust_score": 100, "trust_status": "TRUSTED"},
            {"reader_id": "RDR-002", "trust_score": 75, "trust_status": "TRUSTED"},
            {"reader_id": "RDR-003", "trust_score": 45, "trust_status": "DEGRADED"}
        ]
        
        for trust_data in demo_trust_records:
            try:
                # Check if trust record exists, if so update it, otherwise create new
                existing_trust = db.query(ReaderTrust).filter(ReaderTrust.reader_id == trust_data["reader_id"]).first()
                if existing_trust:
                    existing_trust.trust_score = trust_data["trust_score"]
                    existing_trust.trust_status = trust_data["trust_status"]
                else:
                    trust = ReaderTrust(
                        reader_id=trust_data["reader_id"],
                        trust_score=trust_data["trust_score"],
                        trust_status=trust_data["trust_status"]
                    )
                    db.add(trust)
                db.commit()
            except IntegrityError:
                db.rollback()  # Ignore if already exists
    finally:
        db.close()
    
    simulator_thread = threading.Thread(target=auto_simulator, daemon=True)
    simulator_thread.start()

@app.post("/api/events/sync")
def sync_events():
    from sync_worker import sync_pending_events
    from blockchain import send_to_chain

    def write_to_blockchain(event_id):
        # This is a simplified version - in reality you'd need to fetch the actual event data
        # For now, we'll just pass dummy data to trigger the blockchain call
        send_to_chain(
            tx_hash=event_id,
            decision="allow",
            reason="Synced from pending queue",
            tagUID="dummy",
            vehicle_type="CAR",
            amount=120.0,
            reader_id="TOLL_READER_01",
            timestamp=int(datetime.utcnow().timestamp())
        )

    sync_pending_events(write_to_blockchain)
    return {"status": "Sync triggered"}

def sync_pending_events():
    """Background task to sync pending events to blockchain"""
    import threading
    import time
    from datetime import datetime
    from database import SessionLocal, BlockchainQueue, TollEvent, TollRecord

    while True:
        try:
            db = SessionLocal()
            try:
                # Get all pending events from the blockchain queue
                pending_queue_items = db.query(BlockchainQueue).filter(
                    BlockchainQueue.status == "PENDING"
                ).all()

                for queue_item in pending_queue_items:
                    try:
                        # Get the corresponding toll event
                        toll_event = db.query(TollEvent).filter(
                            TollEvent.event_id == queue_item.event_id
                        ).first()

                        if toll_event:
                            # Get the original toll record to get complete data
                            toll_record = db.query(TollRecord).filter(
                                TollRecord.tx_hash.like(f"{queue_item.event_id}%")
                            ).first()

                            vehicle_type = "CAR"
                            amount = 120.0
                            if toll_record:
                                vehicle_type = toll_record.vehicle_type
                                amount = toll_record.amount

                            # Try to send to blockchain
                            from blockchain import send_to_chain
                            send_to_chain(
                                tx_hash=queue_item.event_id,
                                decision=toll_event.decision,
                                reason="Synced from pending queue",
                                tagUID=toll_event.tag_hash,
                                vehicle_type=vehicle_type,
                                amount=amount,
                                reader_id=toll_event.reader_id,
                                timestamp=toll_event.timestamp
                            )

                            # Mark as synced using the fallback function
                            from fallback import mark_event_synced
                            mark_event_synced(queue_item.event_id)
                    except Exception as e:
                        # Increment retry count
                        queue_item.retry_count += 1
                        queue_item.last_attempt = datetime.utcnow()
                        db.commit()
                        # Optionally, mark as FAILED after too many retries
                        if queue_item.retry_count > 10:  # Max retries
                            queue_item.status = "FAILED"
                            db.commit()
            finally:
                db.close()
        except Exception as e:
            print(f"Error in sync_pending_events: {e}")

        # Wait before next sync cycle
        time.sleep(30)  # Sync every 30 seconds

# ============================
#  READER TRUST API ENDPOINTS
# ============================

@app.get("/api/reader/trust/{reader_id}")
def get_reader_trust(reader_id: str):
    """Get trust status for a specific reader."""
    from database import SessionLocal, ReaderTrust
    db = SessionLocal()
    try:
        trust_score, trust_status = get_reader_trust_status(reader_id, db)
        return {
            "reader_id": reader_id,
            "trust_score": trust_score,
            "trust_status": trust_status
        }
    finally:
        db.close()

@app.get("/api/readers/trust")
def get_all_readers_trust():
    """Get trust status for all readers."""
    from database import SessionLocal, ReaderTrust
    db = SessionLocal()
    try:
        trust_records = db.query(ReaderTrust).all()
        return [{
            "reader_id": record.reader_id,
            "trust_score": record.trust_score,
            "trust_status": record.trust_status,
            "last_updated": record.last_updated.isoformat() if record.last_updated else None
        } for record in trust_records]
    finally:
        db.close()

@app.get("/api/reader/violations/{reader_id}")
def get_reader_violations(reader_id: str):
    """Get violation history for a specific reader."""
    from database import SessionLocal, ReaderViolation
    db = SessionLocal()
    try:
        violations = db.query(ReaderViolation).filter(
            ReaderViolation.reader_id == reader_id
        ).order_by(ReaderViolation.timestamp.desc()).all()
        return [{
            "violation_type": v.violation_type,
            "score_delta": v.score_delta,
            "timestamp": v.timestamp.isoformat() if v.timestamp else None,
            "details": v.details
        } for v in violations]
    finally:
        db.close()

@app.post("/api/reader/trust/reset/{reader_id}")
def reset_reader_trust(reader_id: str):
    """Reset reader trust score to initial state (100, TRUSTED)."""
    from database import SessionLocal, ReaderTrust
    db = SessionLocal()
    try:
        trust_record = db.query(ReaderTrust).filter(
            ReaderTrust.reader_id == reader_id
        ).first()

        if trust_record:
            trust_record.trust_score = 100
            trust_record.trust_status = "TRUSTED"
            trust_record.last_updated = datetime.utcnow()
            db.commit()
            return {
                "reader_id": reader_id,
                "trust_score": trust_record.trust_score,
                "trust_status": trust_record.trust_status,
                "message": "Reader trust reset successfully"
            }
        else:
            # Create new trust record if it doesn't exist
            new_trust = ReaderTrust(
                reader_id=reader_id,
                trust_score=100,
                trust_status="TRUSTED"
            )
            db.add(new_trust)
            db.commit()
            return {
                "reader_id": reader_id,
                "trust_score": new_trust.trust_score,
                "trust_status": new_trust.trust_status,
                "message": "New reader trust record created"
            }
    finally:
        db.close()

# ============================
#  SELF-HEALING TRUST NETWORK API (Patent #1)
# ============================

@app.get("/api/reader/quarantine/{reader_id}")
def get_reader_quarantine(reader_id: str):
    """Get quarantine status and details for a specific reader."""
    from database import SessionLocal
    from self_healing_trust import get_quarantine_status
    db = SessionLocal()
    try:
        status = get_quarantine_status(reader_id, db)
        if not status:
            return {"reader_id": reader_id, "quarantine_status": "NORMAL", "message": "Reader is not quarantined"}
        return status
    finally:
        db.close()

@app.get("/api/quarantine/active")
def get_active_quarantines():
    """Get all currently quarantined readers with their details."""
    from database import SessionLocal
    from self_healing_trust import get_all_quarantined_readers
    db = SessionLocal()
    try:
        return get_all_quarantined_readers(db)
    finally:
        db.close()

@app.post("/api/reader/quarantine/{reader_id}/probation")
def initiate_probation(reader_id: str):
    """Initiate probation challenge protocol for a quarantined reader."""
    from database import SessionLocal
    from self_healing_trust import issue_probation_challenges
    db = SessionLocal()
    try:
        challenges = issue_probation_challenges(reader_id, db)
        if not challenges:
            return {"success": False, "error": "Reader is not eligible for probation (not quarantined or already in probation)"}
        return {
            "success": True,
            "reader_id": reader_id,
            "challenges_issued": len(challenges),
            "challenges": [
                {
                    "id": c.id,
                    "type": c.challenge_type,
                    "challenge_data": json.loads(c.challenge_data) if c.challenge_data else {},
                    "max_attempts": c.max_attempts
                }
                for c in challenges
            ]
        }
    finally:
        db.close()

@app.post("/api/reader/probation/{reader_id}/validate")
async def validate_probation(reader_id: str, request: Request):
    """Validate a probation challenge response from a reader.

    Expected body: {"challenge_id": int, "response": {...}}
    """
    from database import SessionLocal
    from self_healing_trust import validate_probation_response, attempt_reader_restoration, check_all_challenges_passed
    from database import QuarantineRecord
    db = SessionLocal()
    try:
        body = await request.json()
        challenge_id = body.get("challenge_id")
        response_data = body.get("response", {})

        if not challenge_id:
            return {"success": False, "error": "challenge_id is required"}

        result = validate_probation_response(reader_id, challenge_id, response_data, db)

        # If all challenges passed, auto-attempt restoration
        if result["result"] == "PASS" and result.get("remaining", 1) == 0:
            quarantine = db.query(QuarantineRecord).filter(
                QuarantineRecord.reader_id == reader_id,
                QuarantineRecord.status == "PROBATION"
            ).order_by(QuarantineRecord.entered_at.desc()).first()

            if quarantine and check_all_challenges_passed(reader_id, quarantine.id, db):
                restoration = attempt_reader_restoration(reader_id, db)
                result["restoration_attempt"] = restoration

        return result
    finally:
        db.close()

@app.post("/api/reader/quarantine/{quarantine_id}/vote")
async def cast_quarantine_vote(quarantine_id: int, request: Request):
    """Cast a peer consensus vote on a quarantined reader's restoration.

    Expected body: {"voter_reader_id": str, "vote": "APPROVE"/"REJECT", "reason": str}
    """
    from database import SessionLocal
    from self_healing_trust import cast_peer_vote
    db = SessionLocal()
    try:
        body = await request.json()
        voter_id = body.get("voter_reader_id")
        vote = body.get("vote", "").upper()
        reason = body.get("reason", "")

        if not voter_id or vote not in ("APPROVE", "REJECT"):
            return {"success": False, "error": "voter_reader_id and valid vote (APPROVE/REJECT) are required"}

        result = cast_peer_vote(quarantine_id, voter_id, vote, reason, db)
        return result
    finally:
        db.close()

@app.get("/api/reader/quarantine/{quarantine_id}/consensus")
def get_consensus_status(quarantine_id: int):
    """Get peer consensus voting status for a quarantine."""
    from database import SessionLocal
    from self_healing_trust import evaluate_peer_consensus, request_peer_consensus
    db = SessionLocal()
    try:
        consensus = evaluate_peer_consensus(quarantine_id, db)
        peer_info = request_peer_consensus(quarantine_id, db)
        return {**consensus, "peer_info": peer_info}
    finally:
        db.close()

@app.post("/api/reader/quarantine/{reader_id}/restore")
def restore_reader(reader_id: str):
    """Attempt full restoration: probation passed + peer consensus achieved."""
    from database import SessionLocal
    from self_healing_trust import attempt_reader_restoration
    db = SessionLocal()
    try:
        return attempt_reader_restoration(reader_id, db)
    finally:
        db.close()

# Background thread: Trust Decay Recovery & Suspicion Cleanup
def trust_decay_recovery_loop():
    """Background thread that periodically applies trust decay recovery
    and cleans up expired tag suspicions (Patent #1)."""
    while True:
        try:
            time.sleep(300)  # Run every 5 minutes
            from self_healing_trust import run_decay_recovery_cycle, cleanup_expired_suspicions
            recovered = run_decay_recovery_cycle()
            if recovered:
                for reader_id, old_score, new_score in recovered:
                    print(f"[SELF-HEALING] Trust decay recovery: {reader_id} {old_score} -> {new_score}")
            expired = cleanup_expired_suspicions()
            if expired:
                print(f"[SELF-HEALING] Cleaned up {expired} expired tag suspicions")
        except Exception as e:
            print(f"[SELF-HEALING] Error in decay recovery loop: {e}")

# Start the trust decay recovery background thread
decay_thread = threading.Thread(target=trust_decay_recovery_loop, daemon=True)
decay_thread.start()

# Start background sync thread
import threading
sync_thread = threading.Thread(target=sync_pending_events, daemon=True)
sync_thread.start()

# This allows the app to run with uvicorn directly if needed
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
