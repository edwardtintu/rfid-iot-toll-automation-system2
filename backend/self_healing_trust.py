# backend/self_healing_trust.py
"""
Self-Healing Trust Network (Patent #1)

Autonomous Reader Quarantine & Self-Healing Toll Network using Trust Decay Functions.

This module implements four novel capabilities:
1. Time-decay trust recovery (logarithmic biological immune response model)
2. Autonomous quarantine protocol with severity-based escalation
3. Graduated self-healing via probation challenge protocol
4. Peer consensus validation for reader restoration

Patent Claim: "A self-healing electronic toll network comprising a plurality of
RFID reader nodes, each maintaining a trust score governed by a temporal decay
function, wherein reader nodes autonomously enter quarantine states upon trust
threshold violations, and restoration requires completion of a graduated probation
challenge protocol validated by peer consensus among adjacent reader nodes."
"""

import sys
import os
import json
import math
import hashlib
import secrets
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from database import (
    SessionLocal, ReaderTrust, ReaderViolation, Reader,
    QuarantineRecord, ProbationChallenge, PeerConsensusVote,
    TagSuspicion, TollEvent, Card
)


def _load_policy():
    """Load trust policy configuration."""
    policy_file = os.path.join(os.path.dirname(__file__), "trust_policy.json")
    with open(policy_file) as f:
        return json.load(f)


# ============================
#  1. TIME-DECAY TRUST RECOVERY
# ============================

def apply_trust_decay_recovery(reader_id, db):
    """
    Apply time-based trust recovery using a logarithmic decay function.

    The recovery follows a biological immune response model:
        recovery_points = rate × ln(1 + hours_since_last_violation)

    This means:
    - Fast initial recovery (forgiveness for minor issues)
    - Diminishing returns over time (caps at max_recovery_cap)
    - No recovery during quarantine or within min_time window

    Args:
        reader_id: The reader to apply recovery to
        db: SQLAlchemy session

    Returns:
        tuple: (old_score, new_score, points_recovered) or None if no recovery applied
    """
    POLICY = _load_policy()
    decay_config = POLICY.get("trust_decay_recovery", {})

    if not decay_config.get("enabled", False):
        return None

    trust_record = db.query(ReaderTrust).filter(
        ReaderTrust.reader_id == reader_id
    ).first()

    if not trust_record:
        return None

    # No recovery for quarantined readers
    if trust_record.quarantine_status in ("QUARANTINED", "PROBATION"):
        return None

    # Already at max allowed recovery cap
    max_cap = decay_config.get("max_recovery_cap", 80)
    if trust_record.trust_score >= max_cap:
        return None

    # Check minimum time before recovery kicks in
    last_violation = trust_record.last_violation_at
    if not last_violation:
        return None

    min_hours = decay_config.get("min_time_before_recovery_hours", 1.0)
    hours_elapsed = (datetime.utcnow() - last_violation).total_seconds() / 3600.0

    if hours_elapsed < min_hours:
        return None

    # Calculate recovery using logarithmic decay function
    rate = decay_config.get("recovery_rate_per_hour", 2.0)
    recovery_points = rate * math.log(1 + hours_elapsed)

    # Cap recovery so score doesn't exceed max_recovery_cap
    old_score = trust_record.trust_score
    new_score = min(max_cap, old_score + int(recovery_points))

    if new_score <= old_score:
        return None

    # Apply recovery
    trust_record.trust_score = new_score

    # Update trust status based on new score
    thresholds = POLICY.get("thresholds", {})
    if new_score >= thresholds.get("degraded", 70):
        trust_record.trust_status = "TRUSTED"
    elif new_score >= thresholds.get("suspended", 40):
        trust_record.trust_status = "DEGRADED"
    else:
        trust_record.trust_status = "SUSPENDED"

    trust_record.last_updated = datetime.utcnow()
    db.commit()

    return (old_score, new_score, new_score - old_score)


def run_decay_recovery_cycle(db=None):
    """
    Background task: apply trust decay recovery to all eligible readers.

    Called periodically by the background thread. Processes ALL readers
    that are not quarantined and have a trust score below the recovery cap.

    Returns:
        list: List of (reader_id, old_score, new_score) for readers that recovered
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        POLICY = _load_policy()
        max_cap = POLICY.get("trust_decay_recovery", {}).get("max_recovery_cap", 80)

        # Find all readers eligible for recovery
        eligible_readers = db.query(ReaderTrust).filter(
            ReaderTrust.trust_score < max_cap,
            ReaderTrust.quarantine_status == "NORMAL",
            ReaderTrust.last_violation_at.isnot(None)
        ).all()

        recovered = []
        for trust_record in eligible_readers:
            result = apply_trust_decay_recovery(trust_record.reader_id, db)
            if result:
                recovered.append((trust_record.reader_id, result[0], result[1]))

        return recovered
    finally:
        if close_db:
            db.close()


# ============================
#  2. AUTONOMOUS QUARANTINE
# ============================

def check_and_enter_quarantine(reader_id, violation_type, current_score, db):
    """
    Check if a reader should be auto-quarantined based on trust score
    and violation type, and enter quarantine if necessary.

    A reader is quarantined when:
    - Trust score drops below the quarantine threshold, OR
    - A critical violation type occurs (e.g., REPLAY_ATTACK, AUTH_FAILURE)

    When quarantined:
    - Reader is blocked from processing transactions
    - Cross-reader suspicion is propagated to tags recently seen by this reader
    - A quarantine record is created with severity level

    Args:
        reader_id: The reader to potentially quarantine
        violation_type: The violation that triggered this check
        current_score: Current trust score after violation penalty
        db: SQLAlchemy session

    Returns:
        QuarantineRecord if quarantined, None otherwise
    """
    POLICY = _load_policy()
    quarantine_config = POLICY.get("quarantine", {})

    threshold = quarantine_config.get("auto_quarantine_threshold", 35)
    critical_violations = quarantine_config.get("quarantine_on_violations", [])
    severity_weights = quarantine_config.get("severity_weights", {})

    # Determine if quarantine should be triggered
    should_quarantine = False
    reason = ""

    if current_score <= threshold:
        should_quarantine = True
        reason = f"Trust score ({current_score}) dropped below quarantine threshold ({threshold})"
    elif violation_type in critical_violations:
        should_quarantine = True
        reason = f"Critical violation: {violation_type}"

    if not should_quarantine:
        return None

    # Check if already quarantined
    trust_record = db.query(ReaderTrust).filter(
        ReaderTrust.reader_id == reader_id
    ).first()

    if trust_record and trust_record.quarantine_status == "QUARANTINED":
        return None  # Already quarantined

    # Calculate severity level (1-3)
    severity = min(3, severity_weights.get(violation_type, 1))

    # Create quarantine record
    quarantine = QuarantineRecord(
        reader_id=reader_id,
        quarantine_reason=violation_type,
        severity_level=severity,
        status="ACTIVE",
        trust_score_at_entry=current_score
    )
    db.add(quarantine)

    # Update reader trust record
    if trust_record:
        trust_record.quarantine_status = "QUARANTINED"
        trust_record.last_updated = datetime.utcnow()

    db.commit()

    # Propagate cross-reader suspicion for tags associated with this reader
    _propagate_tag_suspicion(reader_id, db)

    return quarantine


def _propagate_tag_suspicion(quarantined_reader_id, db):
    """
    When a reader is quarantined, mark all tags recently seen by that reader
    with elevated suspicion. Other readers encountering these tags will apply
    higher fraud detection sensitivity.

    Args:
        quarantined_reader_id: Reader that was just quarantined
        db: SQLAlchemy session
    """
    POLICY = _load_policy()
    suspicion_config = POLICY.get("cross_reader_suspicion", {})
    multiplier = suspicion_config.get("suspicion_multiplier", 1.5)
    duration_minutes = suspicion_config.get("suspicion_duration_minutes", 30)

    # Find all tags seen by this reader in the last hour
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_events = db.query(TollEvent.tag_hash).filter(
        TollEvent.reader_id == quarantined_reader_id,
        TollEvent.created_at >= one_hour_ago
    ).distinct().all()

    expires_at = datetime.utcnow() + timedelta(minutes=duration_minutes)

    for (tag_hash,) in recent_events:
        # Check if suspicion already exists for this tag
        existing = db.query(TagSuspicion).filter(
            TagSuspicion.tag_hash == tag_hash,
            TagSuspicion.source_reader_id == quarantined_reader_id
        ).first()

        if existing:
            existing.suspicion_multiplier = multiplier
            existing.expires_at = expires_at
        else:
            suspicion = TagSuspicion(
                tag_hash=tag_hash,
                source_reader_id=quarantined_reader_id,
                suspicion_multiplier=multiplier,
                expires_at=expires_at
            )
            db.add(suspicion)

    db.commit()


def get_tag_suspicion_level(tag_hash, db):
    """
    Get the current suspicion multiplier for a tag.
    Used by the fraud detection pipeline to adjust sensitivity.

    Args:
        tag_hash: The tag hash to check
        db: SQLAlchemy session

    Returns:
        float: Suspicion multiplier (1.0 = normal, >1.0 = elevated)
    """
    now = datetime.utcnow()

    # Find active (non-expired) suspicions for this tag
    suspicions = db.query(TagSuspicion).filter(
        TagSuspicion.tag_hash == tag_hash,
        TagSuspicion.expires_at > now
    ).all()

    if not suspicions:
        return 1.0

    # Return the highest suspicion multiplier among active suspicions
    return max(s.suspicion_multiplier for s in suspicions)


def get_quarantine_status(reader_id, db):
    """
    Get the current quarantine status and details for a reader.

    Returns:
        dict with quarantine details, or None if not quarantined
    """
    trust_record = db.query(ReaderTrust).filter(
        ReaderTrust.reader_id == reader_id
    ).first()

    if not trust_record or trust_record.quarantine_status == "NORMAL":
        return None

    # Get the active quarantine record
    quarantine = db.query(QuarantineRecord).filter(
        QuarantineRecord.reader_id == reader_id,
        QuarantineRecord.status.in_(["ACTIVE", "PROBATION"])
    ).order_by(QuarantineRecord.entered_at.desc()).first()

    if not quarantine:
        return None

    # Count completed challenges
    completed_challenges = db.query(ProbationChallenge).filter(
        ProbationChallenge.quarantine_id == quarantine.id,
        ProbationChallenge.result == "PASS"
    ).count()

    # Count votes
    votes = db.query(PeerConsensusVote).filter(
        PeerConsensusVote.quarantine_id == quarantine.id
    ).all()
    approve_count = sum(1 for v in votes if v.vote == "APPROVE")
    reject_count = sum(1 for v in votes if v.vote == "REJECT")

    return {
        "reader_id": reader_id,
        "quarantine_status": trust_record.quarantine_status,
        "quarantine_id": quarantine.id,
        "quarantine_reason": quarantine.quarantine_reason,
        "severity_level": quarantine.severity_level,
        "entered_at": quarantine.entered_at.isoformat() if quarantine.entered_at else None,
        "trust_score_at_entry": quarantine.trust_score_at_entry,
        "current_trust_score": trust_record.trust_score,
        "probation_started_at": quarantine.probation_started_at.isoformat() if quarantine.probation_started_at else None,
        "challenges_completed": completed_challenges,
        "peer_votes": {"approve": approve_count, "reject": reject_count}
    }


# ============================
#  3. GRADUATED SELF-HEALING (PROBATION)
# ============================

def issue_probation_challenges(reader_id, db):
    """
    Issue probation challenges for a quarantined reader.

    The number of challenges scales with the severity level of the quarantine.
    Challenge types include:
    - KNOWN_TAG: Reader must correctly process a known-good tag
    - TIMING_CHECK: Reader must respond within expected time bounds
    - SIGNATURE_VERIFY: Reader must produce a valid HMAC signature

    Args:
        reader_id: The quarantined reader to issue challenges for
        db: SQLAlchemy session

    Returns:
        list: List of issued ProbationChallenge records, or None if not eligible
    """
    POLICY = _load_policy()
    probation_config = POLICY.get("probation", {})

    # Verify reader is quarantined
    trust_record = db.query(ReaderTrust).filter(
        ReaderTrust.reader_id == reader_id
    ).first()

    if not trust_record or trust_record.quarantine_status != "QUARANTINED":
        return None

    # Get active quarantine record
    quarantine = db.query(QuarantineRecord).filter(
        QuarantineRecord.reader_id == reader_id,
        QuarantineRecord.status == "ACTIVE"
    ).order_by(QuarantineRecord.entered_at.desc()).first()

    if not quarantine:
        return None

    # Calculate number of challenges based on severity
    base_challenges = probation_config.get("challenges_required", 3)
    num_challenges = base_challenges + (quarantine.severity_level - 1)  # More severe = more challenges
    max_attempts = probation_config.get("max_attempts_per_challenge", 2)

    # Get known-good tags from the database for challenge generation
    known_tags = db.query(Card.tag_hash).limit(num_challenges + 5).all()
    tag_hashes = [t[0] for t in known_tags] if known_tags else []

    challenges = []
    challenge_types = ["KNOWN_TAG", "TIMING_CHECK", "SIGNATURE_VERIFY"]

    for i in range(num_challenges):
        challenge_type = challenge_types[i % len(challenge_types)]

        # Generate challenge-specific data
        challenge_data = {}
        expected_tag = None

        if challenge_type == "KNOWN_TAG" and tag_hashes:
            expected_tag = tag_hashes[i % len(tag_hashes)]
            challenge_data = {"instruction": "Process this known-good tag and return valid result"}
        elif challenge_type == "TIMING_CHECK":
            challenge_data = {
                "instruction": "Respond within 5 seconds",
                "max_response_ms": 5000,
                "nonce": secrets.token_hex(16)
            }
        elif challenge_type == "SIGNATURE_VERIFY":
            challenge_data = {
                "instruction": "Sign this nonce with your current secret key",
                "nonce": secrets.token_hex(16)
            }

        challenge = ProbationChallenge(
            reader_id=reader_id,
            quarantine_id=quarantine.id,
            challenge_type=challenge_type,
            expected_tag_hash=expected_tag,
            challenge_data=json.dumps(challenge_data),
            max_attempts=max_attempts
        )
        db.add(challenge)
        challenges.append(challenge)

    # Update quarantine record to PROBATION status
    quarantine.status = "PROBATION"
    quarantine.probation_started_at = datetime.utcnow()

    # Update reader trust quarantine status
    trust_record.quarantine_status = "PROBATION"
    trust_record.last_updated = datetime.utcnow()

    db.commit()

    return challenges


def validate_probation_response(reader_id, challenge_id, response_data, db):
    """
    Validate a probation challenge response from a reader.

    Args:
        reader_id: Reader attempting the challenge
        challenge_id: ID of the challenge being attempted
        response_data: dict with response fields (varies by challenge type)
        db: SQLAlchemy session

    Returns:
        dict: {"result": "PASS"/"FAIL"/"MAX_ATTEMPTS_EXCEEDED", "remaining": int}
    """
    POLICY = _load_policy()

    challenge = db.query(ProbationChallenge).filter(
        ProbationChallenge.id == challenge_id,
        ProbationChallenge.reader_id == reader_id
    ).first()

    if not challenge:
        return {"result": "NOT_FOUND", "remaining": 0}

    if challenge.result == "PASS":
        return {"result": "ALREADY_PASSED", "remaining": 0}

    # Check attempt count
    challenge.attempt_count += 1

    if challenge.attempt_count > challenge.max_attempts:
        challenge.result = "FAIL"
        challenge.completed_at = datetime.utcnow()
        db.commit()

        # Penalize for failing probation challenge
        from database import ReaderTrust
        trust_record = db.query(ReaderTrust).filter(
            ReaderTrust.reader_id == reader_id
        ).first()
        if trust_record:
            penalty = POLICY.get("penalties", {}).get("probation_challenge_failure", 10)
            trust_record.trust_score = max(0, trust_record.trust_score - penalty)
            trust_record.last_updated = datetime.utcnow()

        db.commit()
        return {"result": "MAX_ATTEMPTS_EXCEEDED", "remaining": 0}

    # Validate based on challenge type
    passed = False
    challenge_data = json.loads(challenge.challenge_data) if challenge.challenge_data else {}

    if challenge.challenge_type == "KNOWN_TAG":
        # Reader must have correctly identified the tag hash
        passed = response_data.get("tag_hash", "").lower() == (challenge.expected_tag_hash or "").lower()

    elif challenge.challenge_type == "TIMING_CHECK":
        # Reader must respond within the time limit
        max_ms = challenge_data.get("max_response_ms", 5000)
        response_time = response_data.get("response_time_ms", 999999)
        correct_nonce = response_data.get("nonce") == challenge_data.get("nonce")
        passed = response_time <= max_ms and correct_nonce

    elif challenge.challenge_type == "SIGNATURE_VERIFY":
        # Reader must produce a valid HMAC signature of the challenge nonce
        import hmac as hmac_module
        reader = db.query(Reader).filter(Reader.reader_id == reader_id).first()
        if reader and reader.secret:
            expected_nonce = challenge_data.get("nonce", "")
            message = f"{reader_id}{expected_nonce}".encode()
            expected_sig = hmac_module.new(
                reader.secret.encode(), message, hashlib.sha256
            ).hexdigest()
            passed = response_data.get("signature") == expected_sig

    if passed:
        challenge.result = "PASS"
        challenge.completed_at = datetime.utcnow()
    else:
        if challenge.attempt_count >= challenge.max_attempts:
            challenge.result = "FAIL"
            challenge.completed_at = datetime.utcnow()

    db.commit()

    # Count remaining challenges
    quarantine_id = challenge.quarantine_id
    remaining = db.query(ProbationChallenge).filter(
        ProbationChallenge.quarantine_id == quarantine_id,
        ProbationChallenge.result.is_(None)
    ).count()

    return {
        "result": "PASS" if passed else "FAIL",
        "remaining": remaining,
        "attempts_used": challenge.attempt_count,
        "max_attempts": challenge.max_attempts
    }


def check_all_challenges_passed(reader_id, quarantine_id, db):
    """
    Check if all probation challenges for a quarantine have been passed.

    Returns:
        bool: True if all challenges passed
    """
    POLICY = _load_policy()
    required = POLICY.get("probation", {}).get("challenges_required", 3)

    passed_count = db.query(ProbationChallenge).filter(
        ProbationChallenge.quarantine_id == quarantine_id,
        ProbationChallenge.result == "PASS"
    ).count()

    return passed_count >= required


# ============================
#  4. PEER CONSENSUS VALIDATION
# ============================

def request_peer_consensus(quarantine_id, db):
    """
    Initiate peer consensus voting for a quarantined reader's restoration.

    Eligible voters are all ACTIVE readers that are not quarantined themselves.

    Args:
        quarantine_id: ID of the quarantine record
        db: SQLAlchemy session

    Returns:
        dict: {"quarantine_id": int, "eligible_voters": list, "status": str}
    """
    quarantine = db.query(QuarantineRecord).filter(
        QuarantineRecord.id == quarantine_id
    ).first()

    if not quarantine:
        return {"error": "Quarantine record not found"}

    # Find eligible voters (active, non-quarantined readers)
    eligible = db.query(Reader).join(
        ReaderTrust, Reader.reader_id == ReaderTrust.reader_id
    ).filter(
        Reader.status == "ACTIVE",
        Reader.reader_id != quarantine.reader_id,
        ReaderTrust.quarantine_status == "NORMAL"
    ).all()

    return {
        "quarantine_id": quarantine_id,
        "reader_id": quarantine.reader_id,
        "eligible_voters": [r.reader_id for r in eligible],
        "min_voters_required": _load_policy().get("peer_consensus", {}).get("min_voters_required", 2),
        "status": "VOTING_OPEN"
    }


def cast_peer_vote(quarantine_id, voter_reader_id, vote, reason, db):
    """
    Cast a peer consensus vote on whether a quarantined reader should be restored.

    Args:
        quarantine_id: ID of the quarantine record
        voter_reader_id: Reader casting the vote
        vote: "APPROVE" or "REJECT"
        reason: Optional justification
        db: SQLAlchemy session

    Returns:
        dict: {"success": bool, "vote_recorded": str}
    """
    # Validate quarantine exists
    quarantine = db.query(QuarantineRecord).filter(
        QuarantineRecord.id == quarantine_id
    ).first()
    if not quarantine:
        return {"success": False, "error": "Quarantine record not found"}

    # Validate voter is eligible (active, not the quarantined reader, not quarantined itself)
    if voter_reader_id == quarantine.reader_id:
        return {"success": False, "error": "Cannot vote on own quarantine"}

    voter_trust = db.query(ReaderTrust).filter(
        ReaderTrust.reader_id == voter_reader_id,
        ReaderTrust.quarantine_status == "NORMAL"
    ).first()
    if not voter_trust:
        return {"success": False, "error": "Voter is not eligible (quarantined or not found)"}

    # Check for duplicate vote
    existing_vote = db.query(PeerConsensusVote).filter(
        PeerConsensusVote.quarantine_id == quarantine_id,
        PeerConsensusVote.voter_reader_id == voter_reader_id
    ).first()
    if existing_vote:
        return {"success": False, "error": "Already voted on this quarantine"}

    # Record vote
    peer_vote = PeerConsensusVote(
        quarantine_id=quarantine_id,
        voter_reader_id=voter_reader_id,
        vote=vote.upper(),
        reason=reason
    )
    db.add(peer_vote)
    db.commit()

    return {"success": True, "vote_recorded": vote.upper()}


def evaluate_peer_consensus(quarantine_id, db):
    """
    Evaluate if peer consensus threshold has been reached for restoration.

    Args:
        quarantine_id: ID of the quarantine record
        db: SQLAlchemy session

    Returns:
        dict: {"consensus_reached": bool, "approved": bool, "votes": dict}
    """
    POLICY = _load_policy()
    consensus_config = POLICY.get("peer_consensus", {})
    min_voters = consensus_config.get("min_voters_required", 2)
    approval_threshold = consensus_config.get("approval_threshold", 0.6)

    votes = db.query(PeerConsensusVote).filter(
        PeerConsensusVote.quarantine_id == quarantine_id
    ).all()

    total_votes = len(votes)
    approve_count = sum(1 for v in votes if v.vote == "APPROVE")
    reject_count = sum(1 for v in votes if v.vote == "REJECT")

    # Need minimum number of voters
    if total_votes < min_voters:
        return {
            "consensus_reached": False,
            "approved": False,
            "votes": {
                "approve": approve_count,
                "reject": reject_count,
                "total": total_votes,
                "required": min_voters
            },
            "reason": f"Need at least {min_voters} votes, have {total_votes}"
        }

    # Check if approval threshold is met
    approval_ratio = approve_count / total_votes if total_votes > 0 else 0
    approved = approval_ratio >= approval_threshold

    return {
        "consensus_reached": True,
        "approved": approved,
        "votes": {
            "approve": approve_count,
            "reject": reject_count,
            "total": total_votes,
            "approval_ratio": round(approval_ratio, 2),
            "threshold": approval_threshold
        },
        "reason": "Consensus reached" if approved else "Consensus rejected restoration"
    }


# ============================
#  5. FULL RESTORATION ORCHESTRATOR
# ============================

def attempt_reader_restoration(reader_id, db):
    """
    Orchestrate the full reader restoration process:
    1. Verify all probation challenges are passed
    2. Verify peer consensus is achieved
    3. Restore reader with capped trust score

    The restored reader enters a PROBATION trust state (not fully TRUSTED)
    with a capped trust score, and must earn full trust through clean transactions.

    Args:
        reader_id: Reader to restore
        db: SQLAlchemy session

    Returns:
        dict: Restoration result with details
    """
    POLICY = _load_policy()

    # Get active quarantine
    quarantine = db.query(QuarantineRecord).filter(
        QuarantineRecord.reader_id == reader_id,
        QuarantineRecord.status == "PROBATION"
    ).order_by(QuarantineRecord.entered_at.desc()).first()

    if not quarantine:
        return {"success": False, "error": "No active probation found for this reader"}

    # Step 1: Check all probation challenges passed
    challenges_passed = check_all_challenges_passed(reader_id, quarantine.id, db)
    if not challenges_passed:
        return {
            "success": False,
            "error": "Not all probation challenges have been passed",
            "stage": "PROBATION_CHALLENGES"
        }

    # Step 2: Check peer consensus
    consensus = evaluate_peer_consensus(quarantine.id, db)
    if not consensus["consensus_reached"]:
        return {
            "success": False,
            "error": "Peer consensus not yet reached",
            "stage": "PEER_CONSENSUS",
            "consensus_details": consensus
        }

    if not consensus["approved"]:
        return {
            "success": False,
            "error": "Peer consensus rejected restoration",
            "stage": "PEER_CONSENSUS_REJECTED",
            "consensus_details": consensus
        }

    # Step 3: Restore reader with capped trust score
    probation_cap = POLICY.get("probation", {}).get("probation_trust_cap", 60)

    trust_record = db.query(ReaderTrust).filter(
        ReaderTrust.reader_id == reader_id
    ).first()

    if trust_record:
        trust_record.trust_score = min(probation_cap, trust_record.trust_score + 20)
        trust_record.trust_status = "DEGRADED"  # Start as degraded, must earn TRUSTED
        trust_record.quarantine_status = "NORMAL"
        trust_record.last_updated = datetime.utcnow()

    # Close quarantine record
    quarantine.status = "RELEASED"
    quarantine.released_at = datetime.utcnow()

    # Clear tag suspicions from this reader
    db.query(TagSuspicion).filter(
        TagSuspicion.source_reader_id == reader_id
    ).delete()

    db.commit()

    return {
        "success": True,
        "reader_id": reader_id,
        "new_trust_score": trust_record.trust_score if trust_record else probation_cap,
        "new_trust_status": "DEGRADED",
        "quarantine_status": "NORMAL",
        "message": "Reader restored from quarantine via probation + peer consensus"
    }


def get_all_quarantined_readers(db):
    """
    Get all currently quarantined readers with their details.

    Returns:
        list: List of quarantine status dicts
    """
    quarantined_trusts = db.query(ReaderTrust).filter(
        ReaderTrust.quarantine_status.in_(["QUARANTINED", "PROBATION"])
    ).all()

    results = []
    for trust in quarantined_trusts:
        status = get_quarantine_status(trust.reader_id, db)
        if status:
            results.append(status)

    return results


def cleanup_expired_suspicions(db=None):
    """
    Remove expired tag suspicions. Called periodically by background thread.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        now = datetime.utcnow()
        deleted = db.query(TagSuspicion).filter(
            TagSuspicion.expires_at <= now
        ).delete()
        db.commit()
        return deleted
    finally:
        if close_db:
            db.close()
