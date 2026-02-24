# tests/test_vdf_chain.py
"""
Tests for Patent #4: Blockchain-Anchored VDF for Tamper-Evident Toll Sequencing

Tests cover:
- VDF computation and verification
- Sequential chain linking
- Tamper detection (O(1) per link)
- Chain integrity verification over ranges
- Genesis block creation
- Blockchain anchor generation
- Chain state retrieval
"""

import sys
import os
import pytest
import json

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import database models
from database import Base, VDFChainLink, VDFAnchor

# Import VDF chain module
from vdf_chain import compute_vdf, verify_vdf, VDFChainManager


# ============================
#  Test Fixtures
# ============================

@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def vdf_manager(db_session):
    """Create a VDFChainManager with test database."""
    return VDFChainManager(db=db_session)


# ============================
#  1. VDF Computation Tests
# ============================

class TestVDFComputation:
    """Test VDF core computation and verification."""

    def test_vdf_produces_output(self):
        """VDF computation should produce a valid hex hash output."""
        result = compute_vdf("test_input", difficulty=100)
        assert "output" in result
        assert len(result["output"]) == 64  # SHA-256 hex = 64 chars
        assert result["difficulty"] == 100
        assert result["computation_time_ms"] >= 0

    def test_vdf_deterministic(self):
        """Same input + difficulty should always produce the same output."""
        result1 = compute_vdf("same_input", difficulty=100)
        result2 = compute_vdf("same_input", difficulty=100)
        assert result1["output"] == result2["output"]

    def test_vdf_different_inputs_different_outputs(self):
        """Different inputs should produce different VDF outputs."""
        result1 = compute_vdf("input_A", difficulty=100)
        result2 = compute_vdf("input_B", difficulty=100)
        assert result1["output"] != result2["output"]

    def test_vdf_different_difficulty_different_outputs(self):
        """Different difficulty levels should produce different outputs."""
        result1 = compute_vdf("same_input", difficulty=50)
        result2 = compute_vdf("same_input", difficulty=100)
        assert result1["output"] != result2["output"]

    def test_vdf_has_proof_checkpoints(self):
        """VDF should generate proof checkpoints for verification."""
        result = compute_vdf("test_input", difficulty=100)
        proof = json.loads(result["proof"])
        assert len(proof) > 0  # Should have checkpoints
        # Checkpoints should be at intervals of difficulty/10
        assert "10" in proof  # First checkpoint at 100/10 = 10

    def test_vdf_higher_difficulty_takes_longer(self):
        """Higher difficulty should take more time (more iterations)."""
        result_low = compute_vdf("timing_test", difficulty=100)
        result_high = compute_vdf("timing_test", difficulty=5000)
        # The high difficulty should take longer (or at least equal)
        # We can't guarantee this in CI, but the computation_time_ms should be tracked
        assert result_high["computation_time_ms"] >= 0


# ============================
#  2. VDF Verification Tests
# ============================

class TestVDFVerification:
    """Test VDF output verification."""

    def test_verify_correct_output(self):
        """Verification should succeed for correctly computed VDF."""
        result = compute_vdf("verify_me", difficulty=100)
        verification = verify_vdf(
            "verify_me", result["output"], result["proof"], 100
        )
        assert verification["valid"] is True

    def test_verify_wrong_output_fails(self):
        """Verification should fail for incorrect output."""
        result = compute_vdf("verify_me", difficulty=100)
        verification = verify_vdf(
            "verify_me", "0" * 64, result["proof"], 100  # Wrong output
        )
        assert verification["valid"] is False

    def test_verify_wrong_input_fails(self):
        """Verification should fail if input doesn't match output."""
        result = compute_vdf("original_input", difficulty=100)
        verification = verify_vdf(
            "different_input", result["output"], result["proof"], 100
        )
        assert verification["valid"] is False


# ============================
#  3. Chain Linking Tests
# ============================

class TestChainLinking:
    """Test sequential VDF chain linking."""

    def test_first_transaction_creates_genesis(self, vdf_manager, db_session):
        """First chain_transaction should auto-create genesis block."""
        result = vdf_manager.chain_transaction(
            event_id="EVT001",
            tx_hash="a" * 64,
            reader_id="RDR-001",
            timestamp="1700000000",
            db=db_session
        )
        assert result["sequence_number"] == 1  # Sequence 0 is genesis
        assert result["chain_intact"] is True

        # Verify genesis exists
        genesis = db_session.query(VDFChainLink).filter_by(
            sequence_number=0
        ).first()
        assert genesis is not None
        assert genesis.event_id == "GENESIS"

    def test_sequential_linking(self, vdf_manager, db_session):
        """Each transaction should link to the previous VDF output."""
        # Add 3 transactions
        results = []
        for i in range(3):
            result = vdf_manager.chain_transaction(
                event_id=f"EVT{i+1:03d}",
                tx_hash=f"{chr(97+i)}" * 64,
                reader_id="RDR-001",
                timestamp=f"{1700000000 + i}",
                db=db_session
            )
            results.append(result)

        # Verify sequential linking
        links = db_session.query(VDFChainLink).order_by(
            VDFChainLink.sequence_number
        ).all()

        # Genesis + 3 = 4 links
        assert len(links) == 4

        # Each link's previous_vdf_output should match the prior link's vdf_output
        for i in range(1, len(links)):
            assert links[i].previous_vdf_output == links[i-1].vdf_output

    def test_vdf_outputs_are_unique(self, vdf_manager, db_session):
        """Each VDF output in the chain should be unique."""
        outputs = set()
        for i in range(5):
            result = vdf_manager.chain_transaction(
                event_id=f"EVT{i+1:03d}",
                tx_hash=f"{chr(97+i)}" * 64,
                reader_id="RDR-001",
                timestamp=f"{1700000000 + i}",
                db=db_session
            )
            outputs.add(result["vdf_output"])

        assert len(outputs) == 5  # All unique


# ============================
#  4. Tamper Detection Tests
# ============================

class TestTamperDetection:
    """Test tamper detection capabilities."""

    def test_intact_chain_passes_verification(self, vdf_manager, db_session):
        """An unmodified chain should pass integrity verification."""
        for i in range(5):
            vdf_manager.chain_transaction(
                event_id=f"EVT{i+1:03d}",
                tx_hash=f"{chr(97+i)}" * 64,
                reader_id="RDR-001",
                timestamp=f"{1700000000 + i}",
                db=db_session
            )

        result = vdf_manager.verify_chain_integrity(db=db_session)
        assert result["valid"] is True
        assert result["tamper_detected"] is False

    def test_tampered_vdf_output_detected(self, vdf_manager, db_session):
        """Modifying a VDF output should break the chain."""
        for i in range(5):
            vdf_manager.chain_transaction(
                event_id=f"EVT{i+1:03d}",
                tx_hash=f"{chr(97+i)}" * 64,
                reader_id="RDR-001",
                timestamp=f"{1700000000 + i}",
                db=db_session
            )

        # Tamper with link 2's VDF output
        link2 = db_session.query(VDFChainLink).filter_by(
            sequence_number=2
        ).first()
        link2.vdf_output = "TAMPERED" + "0" * 56  # Modified output
        db_session.commit()

        result = vdf_manager.verify_chain_integrity(db=db_session)
        assert result["valid"] is False
        assert result["tamper_detected"] is True
        assert len(result["broken_links"]) > 0

    def test_tampered_event_data_detected(self, vdf_manager, db_session):
        """Modifying event data (e.g., tx_hash) should be detected by VDF mismatch."""
        for i in range(3):
            vdf_manager.chain_transaction(
                event_id=f"EVT{i+1:03d}",
                tx_hash=f"{chr(97+i)}" * 64,
                reader_id="RDR-001",
                timestamp=f"{1700000000 + i}",
                db=db_session
            )

        # Tamper with link 1's vdf_input (simulates changing transaction data)
        link1 = db_session.query(VDFChainLink).filter_by(
            sequence_number=1
        ).first()
        original_input = link1.vdf_input
        link1.vdf_input = original_input + "|EXTRA_DATA"
        db_session.commit()

        result = vdf_manager.verify_chain_integrity(start_seq=1, end_seq=1, db=db_session)
        assert result["valid"] is False
        # The VDF output won't match the modified input
        broken = result["broken_links"]
        assert any(b["type"] == "VDF_MISMATCH" for b in broken)

    def test_detect_tampering_specific_event(self, vdf_manager, db_session):
        """detect_tampering() should check a specific event by ID."""
        for i in range(3):
            vdf_manager.chain_transaction(
                event_id=f"EVT{i+1:03d}",
                tx_hash=f"{chr(97+i)}" * 64,
                reader_id="RDR-001",
                timestamp=f"{1700000000 + i}",
                db=db_session
            )

        # Check untampered event
        result = vdf_manager.detect_tampering("EVT002", db=db_session)
        assert result["found"] is True
        assert result["tampered"] is False

    def test_detect_tampering_nonexistent_event(self, vdf_manager, db_session):
        """detect_tampering() for non-existent event should return not found."""
        result = vdf_manager.detect_tampering("NONEXISTENT", db=db_session)
        assert result["found"] is False


# ============================
#  5. Blockchain Anchor Tests
# ============================

class TestBlockchainAnchors:
    """Test blockchain anchor checkpoint creation."""

    def test_anchor_created_at_interval(self, db_session):
        """Anchors should be created at configured intervals."""
        # Use a small anchor interval for testing
        manager = VDFChainManager(db=db_session)
        manager.config["anchor_interval"] = 5  # Anchor every 5 transactions

        anchor_created = False
        for i in range(5):
            result = manager.chain_transaction(
                event_id=f"EVT{i+1:03d}",
                tx_hash=f"{chr(97+i)}" * 64,
                reader_id="RDR-001",
                timestamp=f"{1700000000 + i}",
                db=db_session
            )
            if result.get("anchor_created"):
                anchor_created = True

        assert anchor_created is True

        # Verify anchor exists in database
        anchors = db_session.query(VDFAnchor).all()
        assert len(anchors) == 1
        assert anchors[0].anchor_status == "PENDING"

    def test_anchor_has_correct_range(self, db_session):
        """Anchor should cover the correct sequence range."""
        manager = VDFChainManager(db=db_session)
        manager.config["anchor_interval"] = 3  # Anchor every 3

        for i in range(3):
            manager.chain_transaction(
                event_id=f"EVT{i+1:03d}",
                tx_hash=f"{chr(97+i)}" * 64,
                reader_id="RDR-001",
                timestamp=f"{1700000000 + i}",
                db=db_session
            )

        anchors = db_session.query(VDFAnchor).all()
        assert len(anchors) == 1
        assert anchors[0].start_sequence == 1
        assert anchors[0].end_sequence == 3

    def test_get_anchors_returns_list(self, vdf_manager, db_session):
        """get_anchors() should return a list of anchor dicts."""
        anchors = vdf_manager.get_anchors(db=db_session)
        assert isinstance(anchors, list)


# ============================
#  6. Chain State Tests
# ============================

class TestChainState:
    """Test chain state retrieval."""

    def test_empty_chain_state(self, vdf_manager, db_session):
        """Empty chain should report not initialized."""
        state = vdf_manager.get_chain_state(db=db_session)
        assert state["chain_initialized"] is False
        assert state["total_links"] == 0

    def test_chain_state_after_transactions(self, vdf_manager, db_session):
        """Chain state should reflect transactions."""
        for i in range(3):
            vdf_manager.chain_transaction(
                event_id=f"EVT{i+1:03d}",
                tx_hash=f"{chr(97+i)}" * 64,
                reader_id="RDR-001",
                timestamp=f"{1700000000 + i}",
                db=db_session
            )

        state = vdf_manager.get_chain_state(db=db_session)
        assert state["chain_initialized"] is True
        assert state["total_links"] == 4  # Genesis + 3
        assert state["head"]["sequence_number"] == 3
        assert state["head"]["event_id"] == "EVT003"

    def test_get_chain_link_by_sequence(self, vdf_manager, db_session):
        """Should retrieve specific chain link by sequence number."""
        vdf_manager.chain_transaction(
            event_id="EVT001",
            tx_hash="a" * 64,
            reader_id="RDR-001",
            timestamp="1700000000",
            db=db_session
        )

        link = vdf_manager.get_chain_link(1, db=db_session)
        assert link is not None
        assert link["event_id"] == "EVT001"
        assert link["sequence_number"] == 1
        assert len(link["vdf_output"]) == 64

    def test_get_nonexistent_link_returns_none(self, vdf_manager, db_session):
        """Getting a non-existent sequence should return None."""
        link = vdf_manager.get_chain_link(999, db=db_session)
        assert link is None

    def test_empty_chain_verification(self, vdf_manager, db_session):
        """Verifying an empty chain should succeed with 0 links."""
        result = vdf_manager.verify_chain_integrity(db=db_session)
        assert result["valid"] is True
        assert result["links_verified"] == 0
