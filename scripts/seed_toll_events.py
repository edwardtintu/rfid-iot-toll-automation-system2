#!/usr/bin/env python3
"""
Seed database with sample toll events for testing.
Run this to populate toll_events table with test data.
"""
import hashlib, hmac, time, requests, sys

# Configuration
API_BASE = "http://localhost:8000"
reader_id = 'READER_01'
tag_hash = 'abc123xyz'
secret = 'reader_secret_01'

def generate_signature(tag_hash, reader_id, timestamp, nonce, secret):
    message = f'{tag_hash}{reader_id}{timestamp}{nonce}'.encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()

def send_toll_request(timestamp, nonce, signature):
    payload = {
        "tag_hash": "ABC123XYZ",
        "reader_id": reader_id,
        "timestamp": timestamp,
        "nonce": nonce,
        "signature": signature,
        "key_version": "1",
        "speed": 60
    }
    try:
        response = requests.post(f"{API_BASE}/api/toll", json=payload, timeout=5)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def main():
    print("Seeding toll events...")
    print("=" * 50)
    
    # Generate 3 test events
    for i in range(3):
        ts = str(int(time.time()) + i)  # Sequential timestamps
        nonce = f"seed_nonce_{ts}_{i}"
        sig = generate_signature(tag_hash, reader_id, ts, nonce, secret)
        
        result = send_toll_request(ts, nonce, sig)
        
        status = "OK" if "action" in result else "FAILED"
        action = result.get("action", "N/A")
        print(f"Event {i+1}: {status} - Action: {action}")
        
        time.sleep(0.5)  # Small delay between requests
    
    print("=" * 50)
    print("Seed complete!")
    print("\nTo verify:")
    print("  docker exec htms-db psql -U htms_user -d htms -c \"SELECT count(*) FROM toll_events;\"")
    print("  docker exec htms-db psql -U htms_user -d htms -c \"SELECT * FROM reader_trust;\"")

if __name__ == "__main__":
    main()
