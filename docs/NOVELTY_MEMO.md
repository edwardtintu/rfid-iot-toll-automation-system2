# HTMS Technical Novelty Memo (Non‑Legal)

This memo documents the **unique system behavior** implemented in HTMS for trust‑driven toll validation and auditability. It is **not legal advice** and does not claim patentability.

## 1. Novel Mechanism Overview

HTMS implements a **Trust‑Weighted Verification Loop (TWVL)**:

1. **Input event** arrives from RFID reader with HMAC signature, timestamp, nonce.
2. **Replay + signature verification** produces hard security signals.
3. **Trust engine** computes a weighted penalty using:
   - Violation type
   - Policy weight
   - Confidence scaling
   - Time‑based decay
4. **Trust status update** gates event processing (allow/block).
5. **Automatic key rotation** occurs when trust falls below a threshold.
6. **Auditable trace** is written: decision telemetry + blockchain queue + optional Merkle anchoring.

This forms a closed‑loop trust system where cryptographic integrity and behavior anomalies directly influence device credentials and processing rights.

## 2. Algorithmic Core (Pseudo‑Logic)

```
trust_score = decay(trust_score, elapsed_time)
adjusted_delta = base_penalty * weight(violation) * clamp(confidence, 0.5..1.0)
trust_score = clamp(trust_score + adjusted_delta, 0..max_score)
trust_status = classify(trust_score)

if trust_score < rotate_key_threshold:
    rotate_reader_key(reader_id)
```

## 3. Why This Is Distinct

- Most systems separate **security verification** and **device trust state**.
- HTMS links cryptographic failures and anomaly signals directly into a **policy‑weighted trust score**.
- The **key‑rotation trigger** is derived from trust state, not manual admin action.
- All decisions are **auditable** in a persistent decision telemetry store and blockchain queue.

## 4. Evidence Needed (Next Step)

To strengthen novelty claims, collect:
- Baseline vs. TWVL false‑positive and false‑negative rates
- Latency impacts of trust‑based gating
- Incident recovery improvements (key rotation effectiveness)

## 5. Implementation References

- Trust policy: `backend/trust_policy_v2.json`
- Trust update logic: `backend/app.py` (`update_reader_trust_score`)
- Decision telemetry: `backend/decision_logger.py`
- Blockchain queue: `backend/fallback.py`

