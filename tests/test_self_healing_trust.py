# tests/test_self_healing_trust.py
"""
Tests for the Self-Healing Trust Network (Patent #1).

Covers:
- Time-decay trust recovery calculations
- Autonomous quarantine triggering
- Probation challenge issuance and validation
- Peer consensus voting and threshold evaluation
- Full quarantine → probation → consensus → restoration lifecycle
- Cross-reader tag suspicion propagation
"""

import sys
import os
import json
import math
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))

# We need to set up an in-memory SQLite database for testing
os.environ["DATABASE_URL"] = "sqlite:///test_self_healing.db"

from database import Base, engine, SessionLocal, ReaderTrust, Reader, ReaderViolation
from database import QuarantineRecord, ProbationChallenge, PeerConsensusVote, TagSuspicion, Card


class TestSelfHealingTrust(unittest.TestCase):
    """Test suite for the Self-Healing Trust Network."""

    @classmethod
    def setUpClass(cls):
        """Create all tables once."""
        Base.metadata.create_all(engine)

    def setUp(self):
        """Set up a clean database state before each test."""
        self.db = SessionLocal()

        # Clean all tables
        self.db.query(TagSuspicion).delete()
        self.db.query(PeerConsensusVote).delete()
        self.db.query(ProbationChallenge).delete()
        self.db.query(QuarantineRecord).delete()
        self.db.query(ReaderViolation).delete()
        self.db.query(ReaderTrust).delete()
        self.db.query(Card).delete()
        self.db.query(Reader).delete()
        self.db.commit()

        # Create test readers
        readers = [
            Reader(reader_id="RDR-TEST-001", status="ACTIVE", secret="secret1", key_version=1),
            Reader(reader_id="RDR-TEST-002", status="ACTIVE", secret="secret2", key_version=1),
            Reader(reader_id="RDR-TEST-003", status="ACTIVE", secret="secret3", key_version=1),
        ]
        for r in readers:
            self.db.add(r)

        # Create trust records
        trust_records = [
            ReaderTrust(reader_id="RDR-TEST-001", trust_score=100, trust_status="TRUSTED", quarantine_status="NORMAL"),
            ReaderTrust(reader_id="RDR-TEST-002", trust_score=75, trust_status="TRUSTED", quarantine_status="NORMAL"),
            ReaderTrust(reader_id="RDR-TEST-003", trust_score=90, trust_status="TRUSTED", quarantine_status="NORMAL"),
        ]
        for t in trust_records:
            self.db.add(t)

        # Create a test card for probation challenges
        card = Card(
            tag_hash="ABCDEF123456",
            owner_name="Test Owner",
            vehicle_number="TN01AB1234",
            vehicle_type="CAR",
            balance=1000.0
        )
        self.db.add(card)
        self.db.commit()

    def tearDown(self):
        """Close the database session."""
        self.db.close()

    @classmethod
    def tearDownClass(cls):
        """Drop all tables and remove test DB."""
        Base.metadata.drop_all(engine)
        try:
            os.remove("test_self_healing.db")
        except:
            pass

    # ==========================================
    #  1. TIME-DECAY TRUST RECOVERY TESTS
    # ==========================================

    def test_no_recovery_for_full_trust(self):
        """Reader at max recovery cap should not receive additional recovery."""
        from self_healing_trust import apply_trust_decay_recovery

        trust = self.db.query(ReaderTrust).filter(ReaderTrust.reader_id == "RDR-TEST-001").first()
        trust.trust_score = 80  # At max_recovery_cap
        trust.last_violation_at = datetime.utcnow() - timedelta(hours=5)
        self.db.commit()

        result = apply_trust_decay_recovery("RDR-TEST-001", self.db)
        self.assertIsNone(result)

    def test_recovery_after_violation(self):
        """Reader with past violation should recover trust over time."""
        from self_healing_trust import apply_trust_decay_recovery

        trust = self.db.query(ReaderTrust).filter(ReaderTrust.reader_id == "RDR-TEST-001").first()
        trust.trust_score = 50
        trust.trust_status = "DEGRADED"
        trust.last_violation_at = datetime.utcnow() - timedelta(hours=3)
        self.db.commit()

        result = apply_trust_decay_recovery("RDR-TEST-001", self.db)
        self.assertIsNotNone(result)
        old_score, new_score, recovered = result
        self.assertEqual(old_score, 50)
        self.assertGreater(new_score, 50)
        self.assertLessEqual(new_score, 80)  # Should not exceed cap

    def test_no_recovery_within_min_time(self):
        """No recovery should happen within the minimum time threshold."""
        from self_healing_trust import apply_trust_decay_recovery

        trust = self.db.query(ReaderTrust).filter(ReaderTrust.reader_id == "RDR-TEST-001").first()
        trust.trust_score = 50
        trust.last_violation_at = datetime.utcnow() - timedelta(minutes=30)  # Less than 1 hour
        self.db.commit()

        result = apply_trust_decay_recovery("RDR-TEST-001", self.db)
        self.assertIsNone(result)

    def test_no_recovery_for_quarantined_reader(self):
        """Quarantined readers should not receive trust recovery."""
        from self_healing_trust import apply_trust_decay_recovery

        trust = self.db.query(ReaderTrust).filter(ReaderTrust.reader_id == "RDR-TEST-001").first()
        trust.trust_score = 30
        trust.quarantine_status = "QUARANTINED"
        trust.last_violation_at = datetime.utcnow() - timedelta(hours=5)
        self.db.commit()

        result = apply_trust_decay_recovery("RDR-TEST-001", self.db)
        self.assertIsNone(result)

    def test_logarithmic_recovery_calculation(self):
        """Verify recovery follows logarithmic function: rate × ln(1 + hours)."""
        from self_healing_trust import apply_trust_decay_recovery

        trust = self.db.query(ReaderTrust).filter(ReaderTrust.reader_id == "RDR-TEST-001").first()
        trust.trust_score = 40
        hours_elapsed = 10
        trust.last_violation_at = datetime.utcnow() - timedelta(hours=hours_elapsed)
        self.db.commit()

        result = apply_trust_decay_recovery("RDR-TEST-001", self.db)
        self.assertIsNotNone(result)
        old_score, new_score, recovered = result

        # Expected: 2.0 * ln(1 + 10) ≈ 2.0 * 2.397 ≈ 4.79 → int(4) points
        expected_recovery = int(2.0 * math.log(1 + hours_elapsed))
        expected_score = min(80, 40 + expected_recovery)
        self.assertEqual(new_score, expected_score)

    # ==========================================
    #  2. AUTONOMOUS QUARANTINE TESTS
    # ==========================================

    def test_auto_quarantine_on_low_score(self):
        """Reader should be quarantined when trust drops below threshold."""
        from self_healing_trust import check_and_enter_quarantine

        trust = self.db.query(ReaderTrust).filter(ReaderTrust.reader_id == "RDR-TEST-001").first()
        trust.trust_score = 30  # Below quarantine threshold (35)
        self.db.commit()

        quarantine = check_and_enter_quarantine("RDR-TEST-001", "REPLAY_ATTACK", 30, self.db)
        self.assertIsNotNone(quarantine)
        self.assertEqual(quarantine.quarantine_reason, "REPLAY_ATTACK")
        self.assertEqual(quarantine.status, "ACTIVE")

        # Verify trust record updated
        self.db.refresh(trust)
        self.assertEqual(trust.quarantine_status, "QUARANTINED")

    def test_auto_quarantine_on_critical_violation(self):
        """Reader should be quarantined on critical violation regardless of score."""
        from self_healing_trust import check_and_enter_quarantine

        trust = self.db.query(ReaderTrust).filter(ReaderTrust.reader_id == "RDR-TEST-001").first()
        trust.trust_score = 60  # Above threshold but critical violation
        self.db.commit()

        quarantine = check_and_enter_quarantine("RDR-TEST-001", "AUTH_FAILURE", 60, self.db)
        self.assertIsNotNone(quarantine)
        self.assertEqual(quarantine.severity_level, 2)  # AUTH_FAILURE weight = 2

    def test_no_quarantine_for_minor_violation(self):
        """Reader should NOT be quarantined for minor violation with good score."""
        from self_healing_trust import check_and_enter_quarantine

        quarantine = check_and_enter_quarantine("RDR-TEST-001", "RATE_LIMIT_EXCEEDED", 70, self.db)
        self.assertIsNone(quarantine)

    def test_no_double_quarantine(self):
        """Already quarantined reader should not get a second quarantine record."""
        from self_healing_trust import check_and_enter_quarantine

        trust = self.db.query(ReaderTrust).filter(ReaderTrust.reader_id == "RDR-TEST-001").first()
        trust.trust_score = 30
        self.db.commit()

        # First quarantine
        q1 = check_and_enter_quarantine("RDR-TEST-001", "REPLAY_ATTACK", 30, self.db)
        self.assertIsNotNone(q1)

        # Second attempt should return None
        q2 = check_and_enter_quarantine("RDR-TEST-001", "REPLAY_ATTACK", 25, self.db)
        self.assertIsNone(q2)

    # ==========================================
    #  3. PROBATION CHALLENGE TESTS
    # ==========================================

    def test_issue_probation_challenges(self):
        """Quarantined reader should receive probation challenges."""
        from self_healing_trust import check_and_enter_quarantine, issue_probation_challenges

        # Quarantine the reader first
        trust = self.db.query(ReaderTrust).filter(ReaderTrust.reader_id == "RDR-TEST-001").first()
        trust.trust_score = 30
        self.db.commit()
        check_and_enter_quarantine("RDR-TEST-001", "REPLAY_ATTACK", 30, self.db)

        # Issue challenges
        challenges = issue_probation_challenges("RDR-TEST-001", self.db)
        self.assertIsNotNone(challenges)
        self.assertGreaterEqual(len(challenges), 3)  # At least 3 base challenges

        # Verify quarantine status changed to PROBATION
        self.db.refresh(trust)
        self.assertEqual(trust.quarantine_status, "PROBATION")

    def test_no_probation_for_non_quarantined(self):
        """Non-quarantined reader should not receive probation challenges."""
        from self_healing_trust import issue_probation_challenges

        challenges = issue_probation_challenges("RDR-TEST-001", self.db)
        self.assertIsNone(challenges)

    def test_validate_known_tag_challenge(self):
        """Reader should pass KNOWN_TAG challenge with correct tag hash."""
        from self_healing_trust import check_and_enter_quarantine, issue_probation_challenges, validate_probation_response

        # Setup: quarantine and issue challenges
        trust = self.db.query(ReaderTrust).filter(ReaderTrust.reader_id == "RDR-TEST-001").first()
        trust.trust_score = 30
        self.db.commit()
        check_and_enter_quarantine("RDR-TEST-001", "REPLAY_ATTACK", 30, self.db)
        challenges = issue_probation_challenges("RDR-TEST-001", self.db)

        # Find a KNOWN_TAG challenge
        known_tag_challenge = next((c for c in challenges if c.challenge_type == "KNOWN_TAG"), None)
        if known_tag_challenge:
            result = validate_probation_response(
                "RDR-TEST-001",
                known_tag_challenge.id,
                {"tag_hash": known_tag_challenge.expected_tag_hash},
                self.db
            )
            self.assertEqual(result["result"], "PASS")

    # ==========================================
    #  4. PEER CONSENSUS TESTS
    # ==========================================

    def test_cast_peer_vote(self):
        """Eligible reader should be able to cast a vote."""
        from self_healing_trust import check_and_enter_quarantine, cast_peer_vote

        # Quarantine reader 1
        trust = self.db.query(ReaderTrust).filter(ReaderTrust.reader_id == "RDR-TEST-001").first()
        trust.trust_score = 30
        self.db.commit()
        quarantine = check_and_enter_quarantine("RDR-TEST-001", "REPLAY_ATTACK", 30, self.db)

        # Reader 2 votes
        result = cast_peer_vote(quarantine.id, "RDR-TEST-002", "APPROVE", "Reader seems OK", self.db)
        self.assertTrue(result["success"])

    def test_cannot_vote_on_own_quarantine(self):
        """Reader should not be able to vote on its own quarantine."""
        from self_healing_trust import check_and_enter_quarantine, cast_peer_vote

        trust = self.db.query(ReaderTrust).filter(ReaderTrust.reader_id == "RDR-TEST-001").first()
        trust.trust_score = 30
        self.db.commit()
        quarantine = check_and_enter_quarantine("RDR-TEST-001", "REPLAY_ATTACK", 30, self.db)

        result = cast_peer_vote(quarantine.id, "RDR-TEST-001", "APPROVE", "", self.db)
        self.assertFalse(result["success"])

    def test_no_duplicate_votes(self):
        """Same reader should not vote twice on the same quarantine."""
        from self_healing_trust import check_and_enter_quarantine, cast_peer_vote

        trust = self.db.query(ReaderTrust).filter(ReaderTrust.reader_id == "RDR-TEST-001").first()
        trust.trust_score = 30
        self.db.commit()
        quarantine = check_and_enter_quarantine("RDR-TEST-001", "REPLAY_ATTACK", 30, self.db)

        cast_peer_vote(quarantine.id, "RDR-TEST-002", "APPROVE", "", self.db)
        result = cast_peer_vote(quarantine.id, "RDR-TEST-002", "APPROVE", "", self.db)
        self.assertFalse(result["success"])
        self.assertIn("Already voted", result["error"])

    def test_consensus_not_reached_insufficient_votes(self):
        """Consensus should not be reached with insufficient votes."""
        from self_healing_trust import check_and_enter_quarantine, evaluate_peer_consensus

        trust = self.db.query(ReaderTrust).filter(ReaderTrust.reader_id == "RDR-TEST-001").first()
        trust.trust_score = 30
        self.db.commit()
        quarantine = check_and_enter_quarantine("RDR-TEST-001", "REPLAY_ATTACK", 30, self.db)

        result = evaluate_peer_consensus(quarantine.id, self.db)
        self.assertFalse(result["consensus_reached"])

    def test_consensus_reached_with_approval(self):
        """Consensus should be reached when enough readers approve."""
        from self_healing_trust import check_and_enter_quarantine, cast_peer_vote, evaluate_peer_consensus

        trust = self.db.query(ReaderTrust).filter(ReaderTrust.reader_id == "RDR-TEST-001").first()
        trust.trust_score = 30
        self.db.commit()
        quarantine = check_and_enter_quarantine("RDR-TEST-001", "REPLAY_ATTACK", 30, self.db)

        # Both peers approve
        cast_peer_vote(quarantine.id, "RDR-TEST-002", "APPROVE", "OK", self.db)
        cast_peer_vote(quarantine.id, "RDR-TEST-003", "APPROVE", "OK", self.db)

        result = evaluate_peer_consensus(quarantine.id, self.db)
        self.assertTrue(result["consensus_reached"])
        self.assertTrue(result["approved"])

    def test_consensus_rejected(self):
        """Consensus should reject when majority rejects."""
        from self_healing_trust import check_and_enter_quarantine, cast_peer_vote, evaluate_peer_consensus

        trust = self.db.query(ReaderTrust).filter(ReaderTrust.reader_id == "RDR-TEST-001").first()
        trust.trust_score = 30
        self.db.commit()
        quarantine = check_and_enter_quarantine("RDR-TEST-001", "REPLAY_ATTACK", 30, self.db)

        # Both peers reject
        cast_peer_vote(quarantine.id, "RDR-TEST-002", "REJECT", "Not OK", self.db)
        cast_peer_vote(quarantine.id, "RDR-TEST-003", "REJECT", "Not OK", self.db)

        result = evaluate_peer_consensus(quarantine.id, self.db)
        self.assertTrue(result["consensus_reached"])
        self.assertFalse(result["approved"])

    # ==========================================
    #  5. FULL LIFECYCLE TEST
    # ==========================================

    def test_full_quarantine_restoration_lifecycle(self):
        """
        Test the complete lifecycle:
        1. Reader gets quarantined (trust drops below threshold)
        2. Probation challenges are issued
        3. Reader passes all challenges
        4. Peer consensus is reached
        5. Reader is restored with capped trust
        """
        from self_healing_trust import (
            check_and_enter_quarantine, issue_probation_challenges,
            validate_probation_response, cast_peer_vote,
            attempt_reader_restoration
        )

        # Step 1: Quarantine
        trust = self.db.query(ReaderTrust).filter(ReaderTrust.reader_id == "RDR-TEST-001").first()
        trust.trust_score = 30
        self.db.commit()
        quarantine = check_and_enter_quarantine("RDR-TEST-001", "REPLAY_ATTACK", 30, self.db)
        self.assertIsNotNone(quarantine)
        self.db.refresh(trust)
        self.assertEqual(trust.quarantine_status, "QUARANTINED")

        # Step 2: Issue probation challenges
        challenges = issue_probation_challenges("RDR-TEST-001", self.db)
        self.assertIsNotNone(challenges)
        self.db.refresh(trust)
        self.assertEqual(trust.quarantine_status, "PROBATION")

        # Step 3: Pass all challenges
        for challenge in challenges:
            if challenge.challenge_type == "KNOWN_TAG":
                response = {"tag_hash": challenge.expected_tag_hash or ""}
            elif challenge.challenge_type == "TIMING_CHECK":
                data = json.loads(challenge.challenge_data)
                response = {"response_time_ms": 1000, "nonce": data.get("nonce")}
            elif challenge.challenge_type == "SIGNATURE_VERIFY":
                # For signature, we need to compute HMAC
                import hmac, hashlib
                data = json.loads(challenge.challenge_data)
                message = f"RDR-TEST-001{data['nonce']}".encode()
                sig = hmac.new("secret1".encode(), message, hashlib.sha256).hexdigest()
                response = {"signature": sig}
            else:
                response = {}

            validate_probation_response("RDR-TEST-001", challenge.id, response, self.db)

        # Step 4: Peer consensus
        cast_peer_vote(quarantine.id, "RDR-TEST-002", "APPROVE", "Looks good", self.db)
        cast_peer_vote(quarantine.id, "RDR-TEST-003", "APPROVE", "OK", self.db)

        # Step 5: Restore
        result = attempt_reader_restoration("RDR-TEST-001", self.db)
        self.assertTrue(result["success"])
        self.assertEqual(result["new_trust_status"], "DEGRADED")
        self.assertLessEqual(result["new_trust_score"], 60)  # Probation cap

        # Verify quarantine status is NORMAL again
        self.db.refresh(trust)
        self.assertEqual(trust.quarantine_status, "NORMAL")

    # ==========================================
    #  6. TAG SUSPICION TESTS
    # ==========================================

    def test_tag_suspicion_level(self):
        """Tag seen by quarantined reader should have elevated suspicion."""
        from self_healing_trust import get_tag_suspicion_level

        # Manually create a suspicion entry
        suspicion = TagSuspicion(
            tag_hash="SUSPECT_TAG_123",
            source_reader_id="RDR-TEST-001",
            suspicion_multiplier=1.5,
            expires_at=datetime.utcnow() + timedelta(minutes=30)
        )
        self.db.add(suspicion)
        self.db.commit()

        level = get_tag_suspicion_level("SUSPECT_TAG_123", self.db)
        self.assertEqual(level, 1.5)

    def test_no_suspicion_for_clean_tag(self):
        """Tag with no suspicion should return multiplier of 1.0."""
        from self_healing_trust import get_tag_suspicion_level

        level = get_tag_suspicion_level("CLEAN_TAG_456", self.db)
        self.assertEqual(level, 1.0)

    def test_expired_suspicion_ignored(self):
        """Expired suspicion entries should not affect the suspicion level."""
        from self_healing_trust import get_tag_suspicion_level

        suspicion = TagSuspicion(
            tag_hash="EXPIRED_TAG_789",
            source_reader_id="RDR-TEST-001",
            suspicion_multiplier=2.0,
            expires_at=datetime.utcnow() - timedelta(minutes=10)  # Already expired
        )
        self.db.add(suspicion)
        self.db.commit()

        level = get_tag_suspicion_level("EXPIRED_TAG_789", self.db)
        self.assertEqual(level, 1.0)

    def test_cleanup_expired_suspicions(self):
        """Cleanup should remove expired suspicion entries."""
        from self_healing_trust import cleanup_expired_suspicions

        # Add expired and active suspicions
        self.db.add(TagSuspicion(
            tag_hash="EXPIRED1", source_reader_id="RDR-TEST-001",
            suspicion_multiplier=1.5, expires_at=datetime.utcnow() - timedelta(hours=1)
        ))
        self.db.add(TagSuspicion(
            tag_hash="ACTIVE1", source_reader_id="RDR-TEST-001",
            suspicion_multiplier=1.5, expires_at=datetime.utcnow() + timedelta(hours=1)
        ))
        self.db.commit()

        deleted = cleanup_expired_suspicions(self.db)
        self.assertEqual(deleted, 1)

        # Active one should still exist
        remaining = self.db.query(TagSuspicion).filter(TagSuspicion.tag_hash == "ACTIVE1").first()
        self.assertIsNotNone(remaining)


if __name__ == "__main__":
    unittest.main()
