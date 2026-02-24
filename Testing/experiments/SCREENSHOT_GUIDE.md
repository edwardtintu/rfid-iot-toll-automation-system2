# HTMS Patent Evidence Screenshots

## Quick Start for Screenshots

**Use your working local backend:**
```bash
cd d:\EDWARD\ISAA_PROJECT\isaa\HTMS_Project
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

---

## 📸 Screenshot Guide

### Experiment 1: ML Fraud Detection
**Run:** `python Testing\experiments\experiment_01_ml_fraud_detection.py`

**What to Screenshot:**
```
======================================================================
ML SCORES EVIDENCE:
======================================================================
  Model A Probability: 0.08
  Model B Probability: 0.10
  Isolation Forest Flag: 0

[SUCCESS] All 3 ML models executed (Model A + Model B + Isolation Forest)
```

**Patent Claim:** Multi-model fraud detection architecture

---

### Experiment 2: Trust Degradation
**Run:** `python Testing\experiments\experiment_02_trust_degradation.py`

**What to Screenshot:**
```
======================================================================
TRUST DEGRADATION EVIDENCE:
======================================================================
  Before: 100
  After:  85
  Change: 100 -> 85 (Penalty applied)
```

**Patent Claim:** Dynamic trust-based access control

---

### Experiment 3: Nonce Storage
**Run:** `python Testing\experiments\experiment_03_nonce_storage.py`

**What to Screenshot:**
```
======================================================================
NONCE RECORDS IN DATABASE (AFTER TRANSACTION):
======================================================================
 id | reader_id | nonce              | timestamp
----+-----------+--------------------+--------------------
 1  | READER_01 | exp3_replay_nonce..| 2026-02-23 11:30:00

[SUCCESS] Nonce recorded in database!
```

**Patent Claim:** Cryptographic replay attack prevention

---

### Experiment 4: Decision Telemetry
**Run:** `python Testing\experiments\experiment_04_decision_telemetry.py`

**What to Screenshot:**
```
======================================================================
DECISION TELEMETRY RECORDS (FROM DATABASE):
======================================================================
 event_id           | reader_id | trust_score | decision | ml_score_a | ml_score_b | anomaly_flag
--------------------+-----------+-------------+----------+------------+------------+-------------
 586da818-1cc9-47.. | READER_01 | 100         | allow    | 0.12       | 0.18       | 0
```

**Patent Claim:** Multi-dimensional decision audit trail

---

### Experiment 5: Trust Transitions
**Run:** `python Testing\experiments\experiment_05_trust_transitions.py`

**What to Screenshot:**
```
======================================================================
TRUST STATUS TRANSITION EVIDENCE:
======================================================================
  Start:  100 (TRUSTED)
  Step 1: 100 (TRUSTED) - After valid transaction
  Step 2: 60 (DEGRADED) - After 1st auth failure (-40)
  Step 3: 20 (SUSPENDED) - After 2nd auth failure (-40)
```

**Patent Claim:** Graduated trust enforcement system

---

## 🎯 Patent Report Structure

### Section 1: Dual ML Model Fusion Architecture
- **Screenshot:** Experiment 1 ML Scores section
- **Evidence:** Model A + Model B + Isolation Forest all execute
- **Label:** "Patent Evidence 1 - Multi-Model Fraud Detection"

### Section 2: Dynamic Trust Degradation
- **Screenshot:** Experiment 2 Trust Degradation section
- **Evidence:** Automatic penalty (100 → 85)
- **Label:** "Patent Evidence 2 - Trust-Based Access Control"

### Section 3: Nonce-Based Replay Prevention
- **Screenshot:** Experiment 3 Nonce Records section
- **Evidence:** Nonce persistence in database
- **Label:** "Patent Evidence 3 - Replay Attack Prevention"

### Section 4: Decision Telemetry
- **Screenshot:** Experiment 4 Telemetry Records section
- **Evidence:** Comprehensive logging with ML scores
- **Label:** "Patent Evidence 4 - Decision Audit Trail"

### Section 5: Trust Status Transitions
- **Screenshot:** Experiment 5 Transition Evidence section
- **Evidence:** TRUSTED → DEGRADED → SUSPENDED
- **Label:** "Patent Evidence 5 - Graduated Enforcement"

---

## 💡 Screenshot Tips

1. **Use Windows Snipping Tool:** `Win + Shift + S`
2. **Select the evidence section only** (highlighted text)
3. **Save as PNG** for best quality
4. **Filename format:**
   - `patent_evidence_01_ml_fusion.png`
   - `patent_evidence_02_trust_degradation.png`
   - `patent_evidence_03_nonce_storage.png`
   - `patent_evidence_04_telemetry.png`
   - `patent_evidence_05_trust_transitions.png`

---

## ⚠️ If Experiments Fail

**Backend not responding?**
```bash
# Check if running
curl http://127.0.0.1:8000/

# If not, start it
cd d:\EDWARD\ISAA_PROJECT\isaa\HTMS_Project
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

**"Invalid signature" errors?**
- Open browser: `http://127.0.0.1:5500/frontend/admin-trust.html`
- Reset reader trust to 100

**"Timestamp expired"?**
- Just run the script again
- Fresh timestamps are auto-generated
