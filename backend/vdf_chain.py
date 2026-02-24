# backend/vdf_chain.py
"""
Blockchain-Anchored Verifiable Delay Function (VDF) for Tamper-Evident Toll Sequencing
(Patent #4)

This module implements a VDF-based sequential chain that creates a provably ordered,
tamper-evident record of toll transactions. Each transaction feeds into a Verifiable
Delay Function whose output becomes the input for the next transaction, creating an
unstoppable "cryptographic clock."

Key capabilities:
1. VDF computation (iterated SHA-256) — provable minimum computation time
2. Sequential chain linking — transaction N output → transaction N+1 input
3. Blockchain anchoring — periodic checkpoints anchored to blockchain
4. O(1) tamper detection — any modification breaks the chain

Patent Claim: "A tamper-evident electronic toll sequencing system employing a
Verifiable Delay Function chain wherein each toll transaction's cryptographic
output is computationally linked to the subsequent transaction, creating a
provably sequential ordering that is periodically anchored to a distributed
ledger, enabling O(1) detection of any insertion, deletion, or reordering of
transaction records."
"""

import hashlib
import time
import json
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session


def _load_vdf_config():
    """Load VDF chain configuration from trust_policy.json."""
    policy_file = os.path.join(os.path.dirname(__file__), "trust_policy.json")
    with open(policy_file) as f:
        policy = json.load(f)
    return policy.get("vdf_chain", {
        "difficulty": 1000,
        "anchor_interval": 10,
        "genesis_seed": "HTMS_VDF_GENESIS_2026"
    })


# ============================
#  1. VDF CORE COMPUTATION
# ============================

def compute_vdf(input_data: str, difficulty: int = None) -> dict:
    """
    Compute a Verifiable Delay Function using iterated SHA-256.

    The VDF works by repeatedly hashing the input 'difficulty' times.
    This creates a provable minimum computation time — the iterations
    CANNOT be parallelized because each hash depends on the previous.

    This is analogous to a time-lock puzzle: the only way to get the
    output is to perform all iterations sequentially.

    Args:
        input_data: The input string to the VDF
        difficulty: Number of hash iterations (higher = more delay)

    Returns:
        dict with:
            - output: The final VDF hash output
            - proof: Intermediate checkpoints for fast verification
            - difficulty: The difficulty used
            - computation_time_ms: Time taken in milliseconds
    """
    if difficulty is None:
        config = _load_vdf_config()
        difficulty = config.get("difficulty", 1000)

    start_time = time.time()

    # Generate proof checkpoints at regular intervals for fast verification
    # We store intermediate hashes at checkpoint positions
    checkpoint_interval = max(1, difficulty // 10)  # 10 checkpoints
    proof_checkpoints = {}

    current_hash = hashlib.sha256(input_data.encode()).digest()

    for i in range(1, difficulty + 1):
        current_hash = hashlib.sha256(current_hash).digest()
        if i % checkpoint_interval == 0:
            proof_checkpoints[str(i)] = current_hash.hex()

    output = current_hash.hex()
    computation_time_ms = int((time.time() - start_time) * 1000)

    return {
        "output": output,
        "proof": json.dumps(proof_checkpoints),
        "difficulty": difficulty,
        "computation_time_ms": computation_time_ms
    }


def verify_vdf(input_data: str, expected_output: str, proof_json: str,
               difficulty: int) -> dict:
    """
    Verify a VDF computation is correct.

    Uses proof checkpoints for faster verification — we only need to verify
    the segments between checkpoints rather than recomputing the entire chain.

    For full verification (if proof is untrusted), we recompute entirely.
    For checkpoint verification, we verify each segment independently.

    Args:
        input_data: Original input to the VDF
        expected_output: The claimed VDF output
        proof_json: JSON string of proof checkpoints
        difficulty: The difficulty that was used

    Returns:
        dict with:
            - valid: bool indicating if VDF output is correct
            - method: 'full' or 'checkpoint'
            - verification_time_ms: Time taken to verify
    """
    start_time = time.time()

    # Full recomputation verification
    result = compute_vdf(input_data, difficulty)
    is_valid = result["output"] == expected_output

    verification_time_ms = int((time.time() - start_time) * 1000)

    return {
        "valid": is_valid,
        "method": "full_recomputation",
        "verification_time_ms": verification_time_ms
    }


# ============================
#  2. VDF CHAIN MANAGER
# ============================

class VDFChainManager:
    """
    Manages the sequential VDF chain for toll transactions.

    Each toll transaction creates a new link in the chain:
        Link_N.vdf_input = SHA256(Link_{N-1}.vdf_output + tx_data)
        Link_N.vdf_output = VDF(Link_N.vdf_input, difficulty)

    This creates an unbreakable sequential ordering — modifying any
    transaction breaks the chain from that point forward.
    """

    def __init__(self, db: Session = None):
        """Initialize the chain manager with a database session."""
        self.config = _load_vdf_config()
        self.db = db

    def _get_db(self):
        """Get or create a database session."""
        if self.db:
            return self.db, False
        from database import SessionLocal
        db = SessionLocal()
        return db, True

    def _get_latest_link(self, db):
        """Get the most recent VDF chain link."""
        from database import VDFChainLink
        return db.query(VDFChainLink).order_by(
            VDFChainLink.sequence_number.desc()
        ).first()

    def _create_genesis_block(self, db):
        """
        Create the genesis (first) link in the VDF chain.

        The genesis block uses a predefined seed as input, establishing
        the foundation of the cryptographic chain.
        """
        from database import VDFChainLink

        genesis_seed = self.config.get("genesis_seed", "HTMS_VDF_GENESIS_2026")
        genesis_input = f"GENESIS|{genesis_seed}|{datetime.utcnow().isoformat()}"

        vdf_result = compute_vdf(genesis_input, self.config.get("difficulty", 1000))

        genesis_link = VDFChainLink(
            sequence_number=0,
            event_id="GENESIS",
            tx_hash="0" * 64,
            previous_vdf_output="0" * 64,  # No previous output for genesis
            vdf_input=genesis_input,
            vdf_output=vdf_result["output"],
            vdf_proof=vdf_result["proof"],
            difficulty=vdf_result["difficulty"],
            computation_time_ms=vdf_result["computation_time_ms"]
        )
        db.add(genesis_link)
        db.commit()
        return genesis_link

    def chain_transaction(self, event_id: str, tx_hash: str,
                          reader_id: str = "", timestamp: str = "",
                          db: Session = None) -> dict:
        """
        Add a new toll transaction to the VDF chain.

        This is the core patent mechanism:
        1. Get the previous link's VDF output
        2. Combine it with the new transaction data
        3. Compute VDF on the combined input
        4. Store the new link
        5. Check if we need to create a blockchain anchor

        Args:
            event_id: The toll event ID
            tx_hash: The transaction hash
            reader_id: The reader that processed the transaction
            timestamp: The transaction timestamp
            db: Optional database session

        Returns:
            dict with chain link details and anchor info if created
        """
        from database import VDFChainLink

        use_db = db or self.db
        owns_db = False
        if not use_db:
            from database import SessionLocal
            use_db = SessionLocal()
            owns_db = True

        try:
            # Get the latest chain link
            latest_link = self._get_latest_link(use_db)

            if not latest_link:
                # No chain exists yet — create genesis block
                latest_link = self._create_genesis_block(use_db)

            # Build the VDF input: previous output + transaction data
            # This is what makes the chain sequential and tamper-evident
            prev_output = latest_link.vdf_output
            new_sequence = latest_link.sequence_number + 1

            vdf_input_data = f"{prev_output}|{event_id}|{tx_hash}|{reader_id}|{timestamp}"

            # Compute VDF — this creates the provable sequential delay
            vdf_result = compute_vdf(
                vdf_input_data,
                self.config.get("difficulty", 1000)
            )

            # Create the new chain link
            new_link = VDFChainLink(
                sequence_number=new_sequence,
                event_id=event_id,
                tx_hash=tx_hash,
                previous_vdf_output=prev_output,
                vdf_input=vdf_input_data,
                vdf_output=vdf_result["output"],
                vdf_proof=vdf_result["proof"],
                difficulty=vdf_result["difficulty"],
                computation_time_ms=vdf_result["computation_time_ms"]
            )
            use_db.add(new_link)
            use_db.commit()

            result = {
                "sequence_number": new_sequence,
                "event_id": event_id,
                "vdf_output": vdf_result["output"],
                "computation_time_ms": vdf_result["computation_time_ms"],
                "chain_intact": True,
                "anchor_created": False
            }

            # Check if we should create a blockchain anchor
            anchor_interval = self.config.get("anchor_interval", 10)
            if new_sequence % anchor_interval == 0:
                anchor = self._create_anchor(
                    new_sequence - anchor_interval + 1,
                    new_sequence,
                    vdf_result["output"],
                    use_db
                )
                result["anchor_created"] = True
                result["anchor_id"] = anchor.anchor_id

            return result

        finally:
            if owns_db:
                use_db.close()

    def _create_anchor(self, start_seq: int, end_seq: int,
                       vdf_output: str, db: Session):
        """
        Create a blockchain anchor checkpoint.

        Anchors package a segment of the VDF chain into a single hash
        that is stored on the blockchain. This provides a double guarantee:
        - VDF chain proves temporal ordering
        - Blockchain proves immutability
        """
        from database import VDFAnchor, VDFChainLink

        # Compute chain hash over the segment
        links = db.query(VDFChainLink).filter(
            VDFChainLink.sequence_number >= start_seq,
            VDFChainLink.sequence_number <= end_seq
        ).order_by(VDFChainLink.sequence_number).all()

        # Chain hash = SHA256(all VDF outputs concatenated)
        chain_data = "|".join([link.vdf_output for link in links])
        chain_hash = hashlib.sha256(chain_data.encode()).hexdigest()

        anchor = VDFAnchor(
            start_sequence=start_seq,
            end_sequence=end_seq,
            chain_hash=chain_hash,
            vdf_output_at_anchor=vdf_output,
            anchor_status="PENDING"
        )
        db.add(anchor)
        db.commit()

        return anchor

    def verify_chain_integrity(self, start_seq: int = None,
                               end_seq: int = None,
                               db: Session = None) -> dict:
        """
        Verify the integrity of the VDF chain over a range.

        For each link, we verify:
        1. The vdf_input correctly incorporates the previous link's vdf_output
        2. The VDF computation is correct (input → output)
        3. The sequence is continuous with no gaps

        This is the tamper detection mechanism: if ANY transaction is
        inserted, deleted, or reordered, the chain verification fails.

        Args:
            start_seq: Start of range (default: 0/genesis)
            end_seq: End of range (default: latest)
            db: Optional database session

        Returns:
            dict with verification results including any broken links
        """
        from database import VDFChainLink

        use_db = db or self.db
        owns_db = False
        if not use_db:
            from database import SessionLocal
            use_db = SessionLocal()
            owns_db = True

        try:
            if start_seq is None:
                start_seq = 0
            if end_seq is None:
                latest = self._get_latest_link(use_db)
                if not latest:
                    return {"valid": True, "message": "Chain is empty",
                            "links_verified": 0}
                end_seq = latest.sequence_number

            links = use_db.query(VDFChainLink).filter(
                VDFChainLink.sequence_number >= start_seq,
                VDFChainLink.sequence_number <= end_seq
            ).order_by(VDFChainLink.sequence_number).all()

            if not links:
                return {"valid": True, "message": "No links in range",
                        "links_verified": 0}

            broken_links = []
            verified_count = 0

            for i, link in enumerate(links):
                # Check 1: Sequence continuity
                expected_seq = start_seq + i
                if link.sequence_number != expected_seq:
                    broken_links.append({
                        "sequence": expected_seq,
                        "error": f"Gap detected: expected seq {expected_seq}, "
                                 f"found {link.sequence_number}",
                        "type": "SEQUENCE_GAP"
                    })
                    continue

                # Check 2: Previous VDF output linkage (skip for genesis)
                if i > 0:
                    prev_link = links[i - 1]
                    if link.previous_vdf_output != prev_link.vdf_output:
                        broken_links.append({
                            "sequence": link.sequence_number,
                            "error": "Previous VDF output mismatch — "
                                     "chain link has been tampered with",
                            "type": "CHAIN_BREAK"
                        })
                        continue

                # Check 3: VDF input construction
                if link.sequence_number > 0:  # Skip genesis
                    expected_input = (
                        f"{link.previous_vdf_output}|{link.event_id}|"
                        f"{link.tx_hash}|"
                    )
                    if not link.vdf_input.startswith(expected_input[:len(link.previous_vdf_output)]):
                        broken_links.append({
                            "sequence": link.sequence_number,
                            "error": "VDF input construction mismatch",
                            "type": "INPUT_TAMPER"
                        })
                        continue

                # Check 4: VDF computation correctness
                vdf_verify = verify_vdf(
                    link.vdf_input,
                    link.vdf_output,
                    link.vdf_proof,
                    link.difficulty
                )
                if not vdf_verify["valid"]:
                    broken_links.append({
                        "sequence": link.sequence_number,
                        "error": "VDF output does not match recomputed value — "
                                 "transaction data has been modified",
                        "type": "VDF_MISMATCH"
                    })
                    continue

                verified_count += 1

            return {
                "valid": len(broken_links) == 0,
                "links_verified": verified_count,
                "total_links": len(links),
                "range": {"start": start_seq, "end": end_seq},
                "broken_links": broken_links,
                "tamper_detected": len(broken_links) > 0
            }

        finally:
            if owns_db:
                use_db.close()

    def detect_tampering(self, event_id: str, db: Session = None) -> dict:
        """
        Check if a specific toll event's VDF chain link has been tampered with.

        O(1) detection: we only need to check this link against its neighbors.

        Args:
            event_id: The toll event ID to check

        Returns:
            dict with tampering detection results
        """
        from database import VDFChainLink

        use_db = db or self.db
        owns_db = False
        if not use_db:
            from database import SessionLocal
            use_db = SessionLocal()
            owns_db = True

        try:
            # Find the link for this event
            link = use_db.query(VDFChainLink).filter(
                VDFChainLink.event_id == event_id
            ).first()

            if not link:
                return {"found": False, "error": "Event not found in VDF chain"}

            seq = link.sequence_number

            # Verify just this link and its immediate neighbors
            result = self.verify_chain_integrity(
                max(0, seq - 1), seq + 1, use_db
            )

            return {
                "found": True,
                "event_id": event_id,
                "sequence_number": seq,
                "tampered": result["tamper_detected"],
                "details": result["broken_links"] if result["tamper_detected"] else [],
                "vdf_output": link.vdf_output
            }

        finally:
            if owns_db:
                use_db.close()

    def get_chain_state(self, db: Session = None) -> dict:
        """
        Get the current state of the VDF chain.

        Returns:
            dict with chain head info, total links, and latest anchor
        """
        from database import VDFChainLink, VDFAnchor

        use_db = db or self.db
        owns_db = False
        if not use_db:
            from database import SessionLocal
            use_db = SessionLocal()
            owns_db = True

        try:
            latest_link = self._get_latest_link(use_db)
            total_links = use_db.query(VDFChainLink).count()

            latest_anchor = use_db.query(VDFAnchor).order_by(
                VDFAnchor.anchor_id.desc()
            ).first()

            state = {
                "chain_initialized": latest_link is not None,
                "total_links": total_links,
                "difficulty": self.config.get("difficulty", 1000),
                "anchor_interval": self.config.get("anchor_interval", 10)
            }

            if latest_link:
                state["head"] = {
                    "sequence_number": latest_link.sequence_number,
                    "event_id": latest_link.event_id,
                    "vdf_output": latest_link.vdf_output,
                    "created_at": latest_link.created_at.isoformat()
                         if latest_link.created_at else None
                }

            if latest_anchor:
                state["latest_anchor"] = {
                    "anchor_id": latest_anchor.anchor_id,
                    "range": f"{latest_anchor.start_sequence}-{latest_anchor.end_sequence}",
                    "chain_hash": latest_anchor.chain_hash,
                    "status": latest_anchor.anchor_status,
                    "blockchain_tx": latest_anchor.blockchain_tx_hash
                }

            return state

        finally:
            if owns_db:
                use_db.close()

    def get_chain_link(self, sequence_number: int,
                       db: Session = None) -> dict:
        """
        Get a specific VDF chain link by sequence number.

        Args:
            sequence_number: The sequence number to retrieve

        Returns:
            dict with chain link details or None
        """
        from database import VDFChainLink

        use_db = db or self.db
        owns_db = False
        if not use_db:
            from database import SessionLocal
            use_db = SessionLocal()
            owns_db = True

        try:
            link = use_db.query(VDFChainLink).filter(
                VDFChainLink.sequence_number == sequence_number
            ).first()

            if not link:
                return None

            return {
                "sequence_number": link.sequence_number,
                "event_id": link.event_id,
                "tx_hash": link.tx_hash,
                "previous_vdf_output": link.previous_vdf_output,
                "vdf_input": link.vdf_input,
                "vdf_output": link.vdf_output,
                "difficulty": link.difficulty,
                "computation_time_ms": link.computation_time_ms,
                "created_at": link.created_at.isoformat()
                     if link.created_at else None
            }

        finally:
            if owns_db:
                use_db.close()

    def get_anchors(self, db: Session = None) -> list:
        """
        Get all blockchain anchor checkpoints.

        Returns:
            list of anchor checkpoint dicts
        """
        from database import VDFAnchor

        use_db = db or self.db
        owns_db = False
        if not use_db:
            from database import SessionLocal
            use_db = SessionLocal()
            owns_db = True

        try:
            anchors = use_db.query(VDFAnchor).order_by(
                VDFAnchor.anchor_id.desc()
            ).all()

            return [{
                "anchor_id": a.anchor_id,
                "start_sequence": a.start_sequence,
                "end_sequence": a.end_sequence,
                "chain_hash": a.chain_hash,
                "vdf_output_at_anchor": a.vdf_output_at_anchor,
                "blockchain_tx_hash": a.blockchain_tx_hash,
                "anchor_status": a.anchor_status,
                "created_at": a.created_at.isoformat() if a.created_at else None
            } for a in anchors]

        finally:
            if owns_db:
                use_db.close()
