#!/usr/bin/env python3
"""
Automated Replay Attack Test
Generates fresh timestamps and sends requests automatically.
No timestamp expiry issues!
"""
import hashlib, hmac, time, requests, json

# Configuration
API_BASE = "http://localhost:8000"
reader_id = 'READER_01'
# Use a real card hash from database (first card: "Hariharan Sundaramoorthy")
tag_hash = "1679a1d39bf32c43c53c7c79c2e8a051300728125869ebe993b2462fde8a5f73"
secret = 'reader_secret_01'

def generate_signature(tag_hash, reader_id, timestamp, nonce, secret):
    message = f'{tag_hash}{reader_id}{timestamp}{nonce}'.encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()

def send_request(timestamp, nonce, signature, test_name):
    payload = {
        "tag_hash": tag_hash,  # Use actual card hash
        "reader_id": reader_id,
        "timestamp": timestamp,
        "nonce": nonce,
        "signature": signature,
        "key_version": "1"
    }
    try:
        response = requests.post(f"{API_BASE}/api/toll", json=payload, timeout=5)
        print(f"\n{'='*60}")
        print(f"{test_name}")
        print(f"{'='*60}")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")  # Print raw response
        result = response.json()
        print(f"Action: {result.get('action', 'N/A')}")
        print(f"Trust Score: {result.get('trust_info', {}).get('trust_score', 'N/A')}")
        print(f"Trust Status: {result.get('trust_info', {}).get('trust_status', 'N/A')}")
        print(f"ML Scores: {result.get('ml_scores', {})}")
        if result.get('reasons'):
            print(f"Reasons: {result.get('reasons')}")
        return result
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    print("=" * 60)
    print("HTMS Replay Attack Test - Automated")
    print("=" * 60)
    
    # Reset reader trust first
    print("\n[SETUP] Resetting reader trust...")
    import subprocess
    subprocess.run('docker exec htms-db psql -U htms_user -d htms -c "UPDATE reader_trust SET trust_score=100, trust_status=\'TRUSTED\' WHERE reader_id=\'READER_01\';"', 
                   shell=True, capture_output=True)
    print("[OK] Reader trust reset to 100")
    
    # Generate fresh timestamp
    ts = str(int(time.time()))
    n1 = f"nonce_{ts}_1"
    n2 = f"nonce_{ts}_2"
    
    sig1 = generate_signature(tag_hash, reader_id, ts, n1, secret)
    sig2 = generate_signature(tag_hash, reader_id, ts, n2, secret)
    
    print(f"\nTimestamp: {ts}")
    print("-" * 60)
    
    # Test 1: Valid transaction
    send_request(ts, n1, sig1, "TEST 1: Valid Transaction (Should ALLOW)")
    time.sleep(0.5)
    
    # Test 2: Replay attack (same nonce)
    send_request(ts, n1, sig1, "TEST 2: Replay Attack - Same Nonce (Should BLOCK)")
    time.sleep(0.5)
    
    # Test 3: Valid with new nonce
    send_request(ts, n2, sig2, "TEST 3: Valid Transaction - New Nonce (Should ALLOW)")
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print("Expected:")
    print("  Test 1: ALLOWED, trust=100, ML scores visible")
    print("  Test 2: BLOCKED (replay), trust=85")
    print("  Test 3: ALLOWED, trust=85, ML scores visible")
    print("\nTo verify database:")
    print('  docker exec htms-db psql -U htms_user -d htms -c "SELECT * FROM reader_trust WHERE reader_id=\'READER_01\';"')
    print('  docker exec htms-db psql -U htms_user -d htms -c "SELECT * FROM used_nonces ORDER BY id DESC LIMIT 3;"')

if __name__ == "__main__":
    main()
