#!/usr/bin/env python3
"""Generate a single valid test request with fresh timestamp"""
import hashlib, hmac, time

tag_hash = "1679a1d39bf32c43c53c7c79c2e8a051300728125869ebe993b2462fde8a5f73"
reader_id = "READER_01"
secret = "reader_secret_01"
ts = str(int(time.time()))
nonce = f"test_nonce_{ts}"

sig = hmac.new(secret.encode(), f'{tag_hash}{reader_id}{ts}{nonce}'.encode(), hashlib.sha256).hexdigest()

print(f"""# Simple Valid Transaction Test
# Timestamp: {ts}

### Valid Transaction (should ALLOW with ML scores)
POST http://localhost:8000/api/toll
Content-Type: application/json

{{
  "tag_hash": "{tag_hash}",
  "reader_id": "{reader_id}",
  "timestamp": "{ts}",
  "nonce": "{nonce}",
  "signature": "{sig}",
  "key_version": "1"
}}
""")
