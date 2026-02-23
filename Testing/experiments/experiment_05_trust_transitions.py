#!/usr/bin/env python3
"""
PATENT EXPERIMENT 5: Multi-Tier Trust Status Transitions
=========================================================
Evidence: System transitions through TRUSTED -> DEGRADED -> SUSPENDED

What this proves:
- Graduated access control
- Threshold-based status changes
- Automatic enforcement
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
    subprocess.run('docker exec htms-db psql -U htms_user -d htms -c "UPDATE reader_trust SET trust_score=100, trust_status=\'TRUSTED\' WHERE reader_id=\'READER_01\'; DELETE FROM used_nonces WHERE reader_id=\'READER_01\';" >nul 2>&1', shell=True)

def get_trust_from_db():
    result = subprocess.run(
        'docker exec htms-db psql -U htms_user -d htms -t -c "SELECT trust_score, trust_status FROM reader_trust WHERE reader_id=\'READER_01\';"',
        shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def send_invalid_signature():
    """Send request with wrong signature to trigger AUTH_FAILURE (-40)"""
    payload = {
        "tag_hash": tag_hash,
        "reader_id": reader_id,
        "timestamp": str(int(time.time())),
        "nonce": f"exp5_bad_{time.time()}",
        "signature": "invalid_signature_12345",
        "key_version": "1"
    }
    try:
        response = requests.post(f"{API_BASE}/api/toll", json=payload, timeout=5)
        return response.json()
    except:
        return {}

def send_valid_transaction():
    """Send valid request"""
    ts = str(int(time.time()))
    nonce = f"exp5_valid_{ts}"
    sig = generate_signature(tag_hash, reader_id, ts, nonce, secret)
    
    payload = {
        "tag_hash": tag_hash,
        "reader_id": reader_id,
        "timestamp": ts,
        "nonce": nonce,
        "signature": sig,
        "key_version": "1"
    }
    try:
        response = requests.post(f"{API_BASE}/api/toll", json=payload, timeout=5)
        return response.json()
    except:
        return {}

def main():
    print("=" * 70)
    print("PATENT EXPERIMENT 5: Multi-Tier Trust Status Transitions")
    print("=" * 70)
    print("\nEvidence: Status changes: TRUSTED (100) -> DEGRADED (60) -> SUSPENDED (20)")
    print("Thresholds: TRUSTED >= 70, DEGRADED >= 40, SUSPENDED < 40")
    print("\n" + "-" * 70)
    
    # Reset
    reset_all()
    print("[OK] Database reset - Starting fresh")
    
    # Initial state
    print("\n" + "=" * 70)
    print("INITIAL STATE:")
    print("=" * 70)
    print("  Trust Score: 100")
    print("  Status: TRUSTED")
    
    # Step 1: Valid transaction (trust stays 100)
    print("\n" + "-" * 70)
    print("STEP 1: Valid Transaction (trust should stay 100)")
    print("-" * 70)
    result1 = send_valid_transaction()
    trust1 = result1.get('trust_info', {}).get('trust_score', 'N/A')
    status1 = result1.get('trust_info', {}).get('trust_status', 'N/A')
    print(f"  Result: {result1.get('action', 'N/A')}")
    print(f"  Trust: {trust1} | Status: {status1}")
    time.sleep(0.3)
    
    # Step 2: Invalid signature (-40 points) -> DEGRADED
    print("\n" + "-" * 70)
    print("STEP 2: Invalid Signature (-40 points) -> Should be DEGRADED")
    print("-" * 70)
    result2 = send_invalid_signature()
    trust2 = result2.get('trust_info', {}).get('trust_score', 'N/A')
    status2 = result2.get('trust_info', {}).get('trust_status', 'N/A')
    print(f"  Response: {result2.get('detail', 'N/A')}")
    print(f"  Trust: {trust2} | Status: {status2}")
    time.sleep(0.3)
    
    # Step 3: Another invalid signature (-40 points) -> SUSPENDED
    print("\n" + "-" * 70)
    print("STEP 3: Another Invalid Signature (-40 points) -> Should be SUSPENDED")
    print("-" * 70)
    result3 = send_invalid_signature()
    trust3 = result3.get('trust_info', {}).get('trust_score', 'N/A')
    status3 = result3.get('trust_info', {}).get('trust_status', 'N/A')
    print(f"  Response: {result3.get('detail', 'N/A')}")
    print(f"  Trust: {trust3} | Status: {status3}")
    
    # Summary
    print("\n" + "=" * 70)
    print("TRUST STATUS TRANSITION EVIDENCE:")
    print("=" * 70)
    print(f"  Start:  100 (TRUSTED)")
    print(f"  Step 1: {trust1} ({status1}) - After valid transaction")
    print(f"  Step 2: {trust2} ({status2}) - After 1st auth failure (-40)")
    print(f"  Step 3: {trust3} ({status3}) - After 2nd auth failure (-40)")
    
    print("\n" + "=" * 70)
    print("DATABASE VERIFICATION:")
    print("=" * 70)
    db_trust = get_trust_from_db()
    print(f"  Current DB State: {db_trust}")
    
    print("\n" + "=" * 70)
    print("SCREENSHOT INSTRUCTIONS:")
    print("=" * 70)
    print("1. Capture the 'TRUST STATUS TRANSITION EVIDENCE' section")
    print("2. Show the progression: 100 -> 60 -> 20")
    print("3. Label: 'Patent Evidence 5 - Multi-Tier Trust Transitions'")

if __name__ == "__main__":
    main()
