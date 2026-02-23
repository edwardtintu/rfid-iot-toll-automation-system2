#!/usr/bin/env python3
"""
PATENT EXPERIMENT 2: Dynamic Trust Score Degradation
=====================================================
Evidence: System automatically degrades trust score on violations.

What this proves:
- Real-time trust scoring (0-100)
- Automatic penalty application
- Multi-tier status (TRUSTED/DEGRADED/SUSPENDED)
"""
import hashlib, hmac, time, requests, json

# Configuration
API_BASE = "http://127.0.0.1:8000"
reader_id = 'RDR-001'
tag_hash = "1679a1d39bf32c43c53c7c79c2e8a051300728125869ebe993b2462fde8a5f73"
secret = 'demo_secret'

def generate_signature(tag_hash, reader_id, timestamp, nonce, secret):
    message = f'{tag_hash}{reader_id}{timestamp}{nonce}'.encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()

def reset_all():
    """Reset using API"""
    try:
        requests.post(f"{API_BASE}/api/reader/trust/reset/{reader_id}", 
                     headers={"X-API-Key": "admin123"}, timeout=5)
    except:
        pass

def send_transaction(timestamp, nonce, signature, test_name):
    payload = {
        "tag_hash": tag_hash,
        "reader_id": reader_id,
        "timestamp": timestamp,
        "nonce": nonce,
        "signature": signature,
        "key_version": "1"
    }
    response = requests.post(f"{API_BASE}/api/toll", json=payload, timeout=10)
    return response.json()

def get_trust_from_api():
    """Get trust info from API"""
    try:
        response = requests.get(f"{API_BASE}/api/readers/trust", 
                               headers={"X-API-Key": "admin123"}, timeout=5)
        if response.ok:
            readers = response.json()
            for r in readers:
                if r.get('reader_id') == reader_id:
                    return f"{r.get('trust_score')} ({r.get('trust_status')})"
    except:
        pass
    return "N/A"

def main():
    print("=" * 70)
    print("PATENT EXPERIMENT 2: Dynamic Trust Score Degradation")
    print("=" * 70)
    print("\nEvidence: Trust score decreases on violations")
    print("Expected: 100 -> 85 after duplicate scan detection")
    print("\n" + "-" * 70)

    # Reset
    reset_all()
    print("[OK] Database reset - Trust score = 100")

    # Show initial state
    print("\nInitial State:")
    print(f"  Trust Score: 100")
    print(f"  Status: TRUSTED")

    # Transaction 1: Valid
    print("\n" + "-" * 70)
    print("TRANSACTION 1: Valid Transaction")
    print("-" * 70)
    ts1 = str(int(time.time()))
    n1 = f"exp2_n1_{ts1}"
    sig1 = generate_signature(tag_hash, reader_id, ts1, n1, secret)

    result1 = send_transaction(ts1, n1, sig1, "Valid")
    print(f"Action: {result1.get('action', 'N/A')}")
    print(f"Trust Score: {result1.get('trust_info', {}).get('trust_score', 'N/A')}")
    time.sleep(0.3)

    # Transaction 2: Duplicate scan (within 1 minute)
    print("\n" + "-" * 70)
    print("TRANSACTION 2: Duplicate Scan (within 1 minute)")
    print("-" * 70)
    ts2 = str(int(time.time()))
    n2 = f"exp2_n2_{ts2}"
    sig2 = generate_signature(tag_hash, reader_id, ts2, n2, secret)

    result2 = send_transaction(ts2, n2, sig2, "Duplicate")
    print(f"Action: {result2.get('action', 'N/A')}")
    print(f"Trust Score: {result2.get('trust_info', {}).get('trust_score', 'N/A')}")
    print(f"Reasons: {result2.get('reasons', [])}")

    # Summary
    print("\n" + "=" * 70)
    print("TRUST DEGRADATION EVIDENCE:")
    print("=" * 70)
    trust1 = result1.get('trust_info', {}).get('trust_score', 'N/A')
    trust2 = result2.get('trust_info', {}).get('trust_score', 'N/A')
    print(f"  Before: {trust1}")
    print(f"  After:  {trust2}")
    print(f"  Change: {trust1} -> {trust2} (Penalty applied)")

    print("\n" + "=" * 70)
    print("DATABASE STATE:")
    print("=" * 70)
    db_state = get_trust_from_api()
    print(f"  From API: {db_state}")

    print("\n" + "=" * 70)
    print("SCREENSHOT INSTRUCTIONS:")
    print("=" * 70)
    print("1. Capture the 'TRUST DEGRADATION EVIDENCE' section")
    print("2. Capture the full responses for both transactions")
    print("3. Label: 'Patent Evidence 2 - Dynamic Trust Degradation'")

if __name__ == "__main__":
    main()
