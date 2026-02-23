#!/usr/bin/env python3
"""
PATENT EXPERIMENT 4: Decision Telemetry Logging
================================================
Evidence: System logs all decisions with ML scores, trust, and reasons.

What this proves:
- Comprehensive audit trail
- Multi-dimensional decision logging
- Forensic analysis capability
"""
import hashlib, hmac, time, requests, json, subprocess

# Configuration
API_BASE = "http://localhost:8000"
reader_id = 'READER_01'
tag_hash = "1679a1d39bf32c43c53c7c79c2e8a051300728125869ebe993b2462fde8a5f73"
secret = 'reader_secret_01'

def generate_signature(tag_hash, reader_id, timestamp, nonce, secret):
    message = f'{tag_hash}{reader_id}{timestamp}{nonce}'.encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()

def reset_all():
    subprocess.run('docker exec htms-db psql -U htms_user -d htms -c "UPDATE reader_trust SET trust_score=100, trust_status=\'TRUSTED\' WHERE reader_id=\'READER_01\';" >nul 2>&1', shell=True)

def check_telemetry():
    result = subprocess.run(
        'docker exec htms-db psql -U htms_user -d htms -c "SELECT event_id, reader_id, trust_score, reader_status, decision, ml_score_a, ml_score_b, anomaly_flag FROM decision_telemetry WHERE reader_id=\'READER_01\' ORDER BY id DESC LIMIT 3;"',
        shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def main():
    print("=" * 70)
    print("PATENT EXPERIMENT 4: Decision Telemetry Logging")
    print("=" * 70)
    print("\nEvidence: All decisions logged with ML scores and trust info")
    print("Expected: Telemetry record created for each transaction")
    print("\n" + "-" * 70)
    
    # Reset
    reset_all()
    print("[OK] Reader trust reset")
    
    # Send transaction
    print("\n" + "-" * 70)
    print("SENDING TRANSACTION:")
    print("-" * 70)
    ts = str(int(time.time()))
    nonce = f"exp4_telemetry_{ts}"
    sig = generate_signature(tag_hash, reader_id, ts, nonce, secret)
    
    payload = {
        "tag_hash": tag_hash,
        "reader_id": reader_id,
        "timestamp": ts,
        "nonce": nonce,
        "signature": sig,
        "key_version": "1"
    }
    
    response = requests.post(f"{API_BASE}/api/toll", json=payload, timeout=5)
    result = response.json()
    
    print(f"Action: {result.get('action', 'N/A')}")
    print(f"ML Scores: {result.get('ml_scores', {})}")
    print(f"Trust: {result.get('trust_info', {})}")
    
    # Check telemetry
    print("\n" + "=" * 70)
    print("DECISION TELEMETRY RECORDS (FROM DATABASE):")
    print("=" * 70)
    telemetry = check_telemetry()
    print(telemetry)
    
    print("\n" + "=" * 70)
    print("TELEMETRY FIELDS CAPTURED:")
    print("=" * 70)
    print("  - event_id: Unique transaction identifier")
    print("  - reader_id: Which reader processed it")
    print("  - trust_score: Reader's trust at decision time")
    print("  - reader_status: TRUSTED/DEGRADED/SUSPENDED")
    print("  - decision: allow/block")
    print("  - ml_score_a: Model A probability")
    print("  - ml_score_b: Model B probability")
    print("  - anomaly_flag: Isolation Forest result")
    
    print("\n" + "=" * 70)
    print("SCREENSHOT INSTRUCTIONS:")
    print("=" * 70)
    print("1. Capture the 'DECISION TELEMETRY RECORDS' section")
    print("2. Show all columns (event_id, trust_score, ml_scores, etc.)")
    print("3. Label: 'Patent Evidence 4 - Decision Telemetry Logging'")

if __name__ == "__main__":
    main()
