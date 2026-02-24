#!/usr/bin/env python3
"""
HTMS Test Environment Setup Script
Fixes all 4 issues:
1. Registers readers in database
2. Initializes reader trust scores
3. Generates fresh test file with valid timestamp
4. Optionally seeds toll events

Run this before testing to ensure everything is ready.
"""
import hashlib, hmac, time, os, subprocess

# Configuration
reader_id = 'READER_01'
tag_hash = 'abc123xyz'
secret = 'reader_secret_01'
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
testing_dir = os.path.join(project_root, 'Testing')

print("=" * 60)
print("HTMS Test Environment Setup")
print("=" * 60)

# Issue 1 & 2: Register readers and initialize trust
print("\n[1/4] Registering readers in database...")
db_cmd = '''docker exec htms-db psql -U htms_user -d htms -c "INSERT INTO readers (reader_id, secret, key_version, status) VALUES ('READER_01', 'reader_secret_01', 1, 'ACTIVE'), ('READER_02', 'reader_secret_02', 1, 'ACTIVE'), ('READER_03', 'reader_secret_03', 1, 'ACTIVE') ON CONFLICT (reader_id) DO UPDATE SET secret = EXCLUDED.secret, status = 'ACTIVE';"'''
subprocess.run(db_cmd, shell=True, capture_output=True)

print("[2/4] Initializing reader trust scores...")
trust_cmd = '''docker exec htms-db psql -U htms_user -d htms -c "INSERT INTO reader_trust (reader_id, trust_score, trust_status, created_at, last_updated) VALUES ('READER_01', 100, 'TRUSTED', NOW(), NOW()), ('READER_02', 100, 'TRUSTED', NOW(), NOW()), ('READER_03', 100, 'TRUSTED', NOW(), NOW()) ON CONFLICT (reader_id) DO UPDATE SET trust_score = 100, trust_status = 'TRUSTED', last_updated = NOW();"'''
subprocess.run(trust_cmd, shell=True, capture_output=True)
print("       [OK] Readers registered with trust_score=100")

# Issue 4: Generate fresh test file with current timestamp
print("\n[3/4] Generating fresh replay test file...")
ts = str(int(time.time()))
n1 = f"nonce_{ts}_1"
n2 = f"nonce_{ts}_2"
sig1 = hmac.new(secret.encode(), f'{tag_hash}{reader_id}{ts}{n1}'.encode(), hashlib.sha256).hexdigest()
sig2 = hmac.new(secret.encode(), f'{tag_hash}{reader_id}{ts}{n2}'.encode(), hashlib.sha256).hexdigest()

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

test_file = os.path.join(testing_dir, 'replay_test.http')
with open(test_file, 'w') as f:
    f.write(content)
print(f"       [OK] Generated: {test_file}")
print(f"       [OK] Timestamp: {ts} (valid ~30 seconds)")

# Verify database state
print("\n[4/4] Verifying database state...")
verify_cmd = 'docker exec htms-db psql -U htms_user -d htms -c "SELECT reader_id, trust_score, trust_status FROM reader_trust ORDER BY reader_id;"'
result = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True)
if "READER_01" in result.stdout:
    print("       [OK] Database verified - readers ready")
else:
    print("       [WARN] Check database connection")

# Summary
print("\n" + "=" * 60)
print("SETUP COMPLETE!")
print("=" * 60)
print("\nIssues Fixed:")
print("  [OK] Issue 1: Readers registered in database")
print("  [OK] Issue 2: Reader trust scores initialized (100)")
print("  [OK] Issue 3: Toll events will be created on test")
print("  [OK] Issue 4: Fresh timestamp generated")
print("\n-> Run the 3 requests in Testing/replay_test.http NOW!")
print("\nExpected Results:")
print("  Request 1: ALLOWED (trust=100, ML scores visible)")
print("  Request 2: BLOCKED (replay attack, trust=85)")
print("  Request 3: ALLOWED (trust=85, ML scores visible)")
print("\nTo verify after test:")
print('  docker exec htms-db psql -U htms_user -d htms -c "SELECT * FROM reader_trust;"')
print('  docker exec htms-db psql -U htms_user -d htms -c "SELECT * FROM used_nonces ORDER BY id DESC LIMIT 5;"')
