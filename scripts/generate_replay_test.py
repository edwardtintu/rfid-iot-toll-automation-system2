#!/usr/bin/env python3
"""
Generate fresh replay attack test with current timestamp.
Run this script before testing to get valid signatures.
"""
import hashlib, hmac, time, os

# Configuration
reader_id = 'READER_01'
tag_hash = 'abc123xyz'
secret = 'reader_secret_01'
# Output to Testing directory (relative to project root)
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
output_dir = os.path.join(project_root, 'Testing')

# Generate current timestamp and unique nonces
ts = str(int(time.time()))
n1 = f"nonce_{ts}_1"
n2 = f"nonce_{ts}_2"

# Generate signatures
sig1 = hmac.new(secret.encode(), f'{tag_hash}{reader_id}{ts}{n1}'.encode(), hashlib.sha256).hexdigest()
sig2 = hmac.new(secret.encode(), f'{tag_hash}{reader_id}{ts}{n2}'.encode(), hashlib.sha256).hexdigest()

# Create test file content
content = f'''# Replay Attack Test for HTMS
# Generated: {time.strftime("%Y-%m-%d %H:%M:%S")}
# Timestamp: {ts}
# Valid for: ~30 seconds from generation
#
# Instructions:
# 1. Run ALL 3 requests immediately after generating
# 2. Request 1 should ALLOW (trust=100, ML scores visible)
# 3. Request 2 should BLOCK (replay detected, trust=85)
# 4. Request 3 should ALLOW (trust=85)

### Request 1: Valid transaction (should ALLOW, trust=100, ML scores visible)
POST http://localhost:8000/api/toll
Content-Type: application/json

{{"tag_hash":"ABC123XYZ","reader_id":"READER_01","timestamp":"{ts}","nonce":"{n1}","signature":"{sig1}","key_version":"1"}}

### Request 2: REPLAY ATTACK - Same nonce reused (should BLOCK, trust=85)
POST http://localhost:8000/api/toll
Content-Type: application/json

{{"tag_hash":"ABC123XYZ","reader_id":"READER_01","timestamp":"{ts}","nonce":"{n1}","signature":"{sig1}","key_version":"1"}}

### Request 3: Valid transaction with new nonce (should ALLOW, trust=85)
POST http://localhost:8000/api/toll
Content-Type: application/json

{{"tag_hash":"ABC123XYZ","reader_id":"READER_01","timestamp":"{ts}","nonce":"{n2}","signature":"{sig2}","key_version":"1"}}
'''

output_file = os.path.join(output_dir, 'replay_test.http')
with open(output_file, 'w') as f:
    f.write(content)

print(f"[OK] Generated: {output_file}")
print(f"  Timestamp: {ts}")
print(f"  Valid for: ~30 seconds")
print(f"  Run all 3 requests NOW!")
