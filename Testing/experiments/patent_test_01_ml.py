#!/usr/bin/env python3
"""Simple test to show ML fraud detection - Patent Evidence 1"""
import requests
import hashlib
import hmac
import time
import json

API_BASE = "http://127.0.0.1:8000"
reader_id = 'RDR-001'
tag_hash = "1679a1d39bf32c43c53c7c79c2e8a051300728125869ebe993b2462fde8a5f73"
secret = 'demo_secret'

def generate_signature(tag_hash, reader_id, timestamp, nonce, secret):
    message = f'{tag_hash}{reader_id}{timestamp}{nonce}'.encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()

print("=" * 70)
print("PATENT EVIDENCE 1: ML Fraud Detection with Dual Models")
print("=" * 70)
print()

ts = str(int(time.time()))
nonce = f"patent_test_{ts}"
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
    response = requests.post(f"{API_BASE}/api/toll", json=payload, timeout=30)
    result = response.json()
    
    print("RESPONSE:")
    print(json.dumps(result, indent=2))
    print()
    
    print("=" * 70)
    print("ML SCORES EVIDENCE:")
    print("=" * 70)
    ml_scores = result.get('ml_scores', {})
    print(f"  Model A Probability: {ml_scores.get('modelA_prob', 'N/A')}")
    print(f"  Model B Probability: {ml_scores.get('modelB_prob', 'N/A')}")
    print(f"  Isolation Forest Flag: {ml_scores.get('iso_flag', 'N/A')}")
    print()
    
    if 'modelA_prob' in ml_scores and 'modelB_prob' in ml_scores and 'iso_flag' in ml_scores:
        print("[SUCCESS] All 3 ML models executed (Model A + Model B + Isolation Forest)")
        print()
        print("=" * 70)
        print("SCREENSHOT THIS SECTION FOR PATENT EVIDENCE!")
        print("=" * 70)
    else:
        print("[WARNING] Some ML scores missing")
        
except Exception as e:
    print(f"[ERROR] {e}")
    print("Backend may still be loading - wait 10 seconds and try again")
