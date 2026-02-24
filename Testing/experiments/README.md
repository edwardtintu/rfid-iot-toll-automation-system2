# HTMS Patent Evidence Experiments

## Overview
Run these experiments in order to collect patent evidence screenshots.

**Important:** Ensure backend is running before starting experiments.

---

## Pre-Requisites

### 1. Start the Backend Server
```bash
cd d:\EDWARD\ISAA_PROJECT\isaa\HTMS_Project
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Verify Backend is Running
Open browser: `http://127.0.0.1:8000/`
You should see: `{"message":"HTMS API running"}`

---

## Experiment List

| # | Experiment | File | What It Proves | Patent Claim |
|---|------------|------|----------------|--------------|
| 1 | ML Fraud Detection | `experiment_01_ml_fraud_detection.py` | Dual ML models (A+B) + Isolation Forest | Multi-model fraud detection architecture |
| 2 | Trust Degradation | `experiment_02_trust_degradation.py` | Automatic trust score decrease on violations | Dynamic trust-based access control |
| 3 | Nonce Storage | `experiment_03_nonce_storage.py` | Replay attack prevention via nonce recording | Cryptographic replay attack prevention |
| 4 | Decision Telemetry | `experiment_04_decision_telemetry.py` | Comprehensive audit logging | Multi-dimensional decision audit trail |
| 5 | Trust Transitions | `experiment_05_trust_transitions.py` | TRUSTED → DEGRADED → SUSPENDED progression | Graduated trust enforcement system |

---

## How to Run Experiments

### Experiment 1: ML Fraud Detection
```bash
python Testing\experiments\experiment_01_ml_fraud_detection.py
```

**What to Capture for Patent:**
- ML Scores section showing Model A, Model B, and Isolation Forest results
- Full JSON response with ml_scores object
- Evidence that all 3 models run simultaneously

**Expected Output:**
```
ML SCORES EVIDENCE:
  Model A Probability: 0.08
  Model B Probability: 0.10
  Isolation Forest Flag: 0
[SUCCESS] All 3 ML models executed
```

---

### Experiment 2: Trust Degradation
```bash
python Testing\experiments\experiment_02_trust_degradation.py
```

**What to Capture for Patent:**
- Trust score before and after violation
- The automatic penalty application
- Response showing trust_info with degraded score

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

**What to Capture for Patent:**
- Database query showing nonce records
- The nonce value and its timestamp
- Evidence that nonce persists after transaction

**Expected Output:**
```
NONCE RECORDS IN DATABASE (AFTER TRANSACTION):
 id | reader_id | nonce | timestamp
----+-----------+-------+------------
 1  | RDR-001   | exp3...| 2026-02-23
[SUCCESS] Nonce recorded in database!
```

---

### Experiment 4: Decision Telemetry
```bash
python Testing\experiments\experiment_04_decision_telemetry.py
```

**What to Capture for Patent:**
- Database query showing telemetry records
- All columns: event_id, trust_score, ml_score_a, ml_score_b, anomaly_flag
- Evidence of comprehensive logging

**Expected Output:**
```
DECISION TELEMETRY RECORDS:
 event_id | reader_id | trust_score | decision | ml_score_a | ml_score_b
----------+-----------+-------------+----------+------------+------------
 ...      | RDR-001   | 100         | allow    | 0.12       | 0.18
```

---

### Experiment 5: Trust Transitions
```bash
python Testing\experiments\experiment_05_trust_transitions.py
```

**What to Capture for Patent:**
- The full progression: 100 → 60 → 20
- Status changes: TRUSTED → DEGRADED → SUSPENDED
- Database verification of final state

**Expected Output:**
```
TRUST STATUS TRANSITION EVIDENCE:
  Start:  100 (TRUSTED)
  Step 1: 100 (TRUSTED) - After valid transaction
  Step 2: 60 (DEGRADED) - After 1st auth failure (-40)
  Step 3: 20 (SUSPENDED) - After 2nd auth failure (-40)
```

---

## Patent Report Structure

### Section 1: Dual ML Model Fusion Architecture
**Evidence Source:** Experiment 1
**What to Include:**
- Screenshot of ML Scores Evidence section
- Highlight that Model A + Model B + Isolation Forest all execute
- Note the independent scoring from each model

### Section 2: Dynamic Trust-Based Access Control
**Evidence Source:** Experiment 2
**What to Include:**
- Screenshot showing trust score change (100 → 85)
- Highlight automatic penalty application
- Note real-time trust updates

### Section 3: Cryptographic Replay Attack Prevention
**Evidence Source:** Experiment 3
**What to Include:**
- Screenshot of nonce database records
- Highlight nonce persistence
- Note the cryptographic signature generation

### Section 4: Multi-Dimensional Decision Audit Trail
**Evidence Source:** Experiment 4
**What to Include:**
- Screenshot of decision telemetry table
- Highlight all captured fields (ML scores, trust, decision, etc.)
- Note forensic analysis capability

### Section 5: Graduated Trust Enforcement System
**Evidence Source:** Experiment 5
**What to Include:**
- Screenshot of trust progression (100 → 60 → 20)
- Highlight status transitions (TRUSTED → DEGRADED → SUSPENDED)
- Note threshold-based automatic enforcement

---

## Tips for Best Screenshots

1. **Use Windows Terminal** - Better text rendering
2. **Full screen capture** - Use `Win + Shift + S` for snip
3. **Highlight key sections** - Use mouse to select evidence sections before capture
4. **Save as PNG** - Better quality for documents
5. **Label each screenshot** - Add patent evidence number in filename

**Recommended Filename Format:**
```
patent_evidence_01_ml_fusion.png
patent_evidence_02_trust_degradation.png
patent_evidence_03_nonce_storage.png
patent_evidence_04_telemetry.png
patent_evidence_05_trust_transitions.png
```

---

## Expected Results Summary

| Experiment | Key Evidence | Expected Value | Patent Claim Supported |
|------------|--------------|----------------|------------------------|
| 1 | Model A Probability | ~0.08 | Multi-model architecture |
| 1 | Model B Probability | ~0.10 | Independent scoring |
| 1 | Isolation Forest | 0 (no anomaly) | Anomaly detection layer |
| 2 | Initial Trust | 100 | Baseline trust establishment |
| 2 | After Violation | 85 | Automatic penalty system |
| 3 | Nonce Recorded | YES | Replay attack prevention |
| 4 | Telemetry Logged | YES | Audit trail capability |
| 5 | Final Status | SUSPENDED (20) | Graduated enforcement |

---

## Troubleshooting

### Issue: "Connection refused" or "Read timed out"
**Solution:**
```bash
# Check if backend is running
curl http://127.0.0.1:8000/

# If not running, start it:
cd d:\EDWARD\ISAA_PROJECT\isaa\HTMS_Project
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

### Issue: "Invalid signature" or "Reader suspended"
**Solution:**
- Database may have old penalty records
- Run Experiment 5 to see current state
- Use admin-trust.html to reset reader trust

### Issue: "Timestamp expired"
**Solution:**
- Run the script again immediately
- Scripts generate fresh timestamps automatically
- Ensure system clock is synchronized

### Issue: "ModuleNotFoundError: No module named 'requests'"
**Solution:**
```bash
pip install requests
```

---

## Admin Tools for Resetting State

### Reset Reader Trust via Browser
1. Open: `http://127.0.0.1:5500/frontend/admin-trust.html`
2. Enter Reader ID: `RDR-001`
3. Click "Reset Trust to 100 (TRUSTED)"

### Reset Reader Trust via API
```bash
curl -X POST http://127.0.0.1:8000/api/reader/trust/reset/RDR-001 ^
  -H "X-API-Key: admin123"
```

### View Current Trust Status
```bash
curl http://127.0.0.1:8000/api/readers/trust ^
  -H "X-API-Key: admin123"
```

---

## Document Version
- **Version:** 1.0
- **Date:** February 23, 2026
- **Backend:** Local SQLite (no Docker)
- **API Key:** admin123
