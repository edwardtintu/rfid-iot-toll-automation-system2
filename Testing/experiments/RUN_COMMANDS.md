# HTMS Patent Experiments - Run Commands

## Prerequisites

**Ensure backend is running:**
```bash
cd d:\EDWARD\ISAA_PROJECT\isaa\HTMS_Project
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

**Verify backend is responding:**
```bash
curl http://127.0.0.1:8000/
# Should return: {"message":"HTMS API running"}
```

---

## Experiment Run Commands

### Experiment 1: ML Fraud Detection
```bash
python Testing\experiments\experiment_01_ml_fraud_detection.py
```

**What to Capture for Patent Report:**
- Screenshot the "ML SCORES EVIDENCE" section
- Shows Model A + Model B + Isolation Forest all executing
- **Patent Claim:** Multi-model fraud detection architecture

**Expected Output:**
```
ML SCORES EVIDENCE:
  Model A Probability: 0.08
  Model B Probability: 0.10
  Isolation Forest Flag: 0
[SUCCESS] All 3 ML models executed (Model A + Model B + Isolation Forest)
```

---

### Experiment 2: Trust Degradation
```bash
python Testing\experiments\experiment_02_trust_degradation.py
```

**What to Capture for Patent Report:**
- Screenshot "TRUST DEGRADATION EVIDENCE" section
- Shows automatic trust penalty on violations
- **Patent Claim:** Dynamic trust-based access control

**Expected Output:**
```
TRUST DEGRADATION EVIDENCE:
  Before: 100
  After:  85
  Change: 100 -> 85 (Penalty applied)
```

---

### Experiment 3: Nonce Storage
```bash
python Testing\experiments\experiment_03_nonce_storage.py
```

**What to Capture for Patent Report:**
- Screenshot "NONCE RECORDS IN DATABASE" section
- Shows nonce persistence for replay prevention
- **Patent Claim:** Cryptographic replay attack prevention

**Expected Output:**
```
NONCE RECORDS IN DATABASE (AFTER TRANSACTION):
 id | reader_id | nonce              | timestamp
----+-----------+--------------------+------------
 1  | READER_01 | exp3_replay_nonce..| 2026-02-23
[SUCCESS] Nonce recorded in database!
```

---

### Experiment 4: Decision Telemetry
```bash
python Testing\experiments\experiment_04_decision_telemetry.py
```

**What to Capture for Patent Report:**
- Screenshot "DECISION TELEMETRY RECORDS" section
- Shows comprehensive audit logging
- **Patent Claim:** Multi-dimensional decision audit trail

**Expected Output:**
```
DECISION TELEMETRY RECORDS:
 event_id | reader_id | trust_score | decision | ml_score_a | ml_score_b
----------+-----------+-------------+----------+------------+------------
 ...      | READER_01 | 100         | allow    | 0.12       | 0.18
```

---

### Experiment 5: Trust Transitions
```bash
python Testing\experiments\experiment_05_trust_transitions.py
```

**What to Capture for Patent Report:**
- Screenshot "TRUST STATUS TRANSITION EVIDENCE" section
- Shows graduated enforcement (TRUSTED → DEGRADED → SUSPENDED)
- **Patent Claim:** Multi-tier trust enforcement system

**Expected Output:**
```
TRUST STATUS TRANSITION EVIDENCE:
  Start:  100 (TRUSTED)
  Step 1: 100 (TRUSTED) - After valid transaction
  Step 2: 60 (DEGRADED) - After 1st auth failure (-40)
  Step 3: 20 (SUSPENDED) - After 2nd auth failure (-40)
```

---

## Patent Report Subtitles

Use these subtitles in your patent document:

1. **Dual ML Model Fusion Architecture for Real-Time Fraud Detection**
   - Evidence from Experiment 1
   - Shows Model A + Model B + Isolation Forest executing simultaneously

2. **Dynamic Trust Score Degradation System**
   - Evidence from Experiment 2
   - Shows automatic trust penalty (100 → 85) on violations

3. **Cryptographic Nonce-Based Replay Attack Prevention**
   - Evidence from Experiment 3
   - Shows nonce persistence in database

4. **Multi-Dimensional Decision Telemetry and Audit Trail**
   - Evidence from Experiment 4
   - Shows comprehensive logging with ML scores, trust, decisions

5. **Graduated Trust Enforcement with Multi-Tier Status Transitions**
   - Evidence from Experiment 5
   - Shows TRUSTED → DEGRADED → SUSPENDED progression

---

## Troubleshooting

### If experiments fail with "Connection refused":
```bash
# Start the backend
cd d:\EDWARD\ISAA_PROJECT\isaa\HTMS_Project
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

### If experiments fail with "Invalid signature":
- Reader may be suspended from previous runs
- Open browser: `http://127.0.0.1:5500/frontend/admin-trust.html`
- Reset reader trust to 100

### If timeout errors occur:
- Run the experiment again immediately
- Timestamps expire after ~30 seconds
- Scripts auto-generate fresh timestamps each run
