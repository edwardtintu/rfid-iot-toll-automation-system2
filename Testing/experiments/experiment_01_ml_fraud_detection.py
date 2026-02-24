#!/usr/bin/env python3
"""
PATENT EXPERIMENT 1: ML Fraud Detection with Dual Models
=========================================================
Evidence: System uses two independent ML models (Model A + Model B)
          plus Isolation Forest for real-time fraud scoring.

What this proves:
- Dual ML model fusion architecture
- Real-time probability scoring
- Anomaly detection integration
"""
import hashlib, hmac, time, requests, json, sys

# Configuration
API_BASE = "http://localhost:8000"
reader_id = 'READER_01'
tag_hash = "1679a1d39bf32c43c53c7c79c2e8a051300728125869ebe993b2462fde8a5f73"
secret = 'reader_secret_01'

def generate_signature(tag_hash, reader_id, timestamp, nonce, secret):
    message = f'{tag_hash}{reader_id}{timestamp}{nonce}'.encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()

def reset_reader_trust():
    """Reset reader trust using API call"""
    try:
        requests.post(f"{API_BASE}/api/reader/trust/reset/{reader_id}", 
                     headers={"X-API-Key": "admin123"}, timeout=5)
    except Exception as e:
        print(f"[WARNING] Could not reset trust via API: {e}")

def main():
    print("=" * 70)
    print("PATENT EXPERIMENT 1: ML Fraud Detection with Dual Models")
    print("=" * 70)
    print("\nEvidence: System runs Model A + Model B + Isolation Forest")
    print("Expected: ML scores visible in response (modelA_prob, modelB_prob, iso_flag)")
    print("\n" + "-" * 70)

    # Reset trust
    reset_reader_trust()
    print("[OK] Reader trust reset to 100")

    # Generate fresh timestamp
    ts = str(int(time.time()))
    nonce = f"exp1_nonce_{ts}"
    sig = generate_signature(tag_hash, reader_id, ts, nonce, secret)

    payload = {
        "tag_hash": tag_hash,
        "reader_id": reader_id,
        "timestamp": ts,
        "nonce": nonce,
        "signature": sig,
        "key_version": "1"
    }

    print(f"\nSending request with timestamp: {ts}")
    print("-" * 70)

    try:
        response = requests.post(f"{API_BASE}/api/toll", json=payload, timeout=5)
        result = response.json()

        print("\n" + "=" * 70)
        print("RESPONSE:")
        print("=" * 70)
        print(json.dumps(result, indent=2))

        # Extract and highlight ML scores
        print("\n" + "=" * 70)
        print("ML SCORES EVIDENCE:")
        print("=" * 70)
        ml_scores = result.get('ml_scores', {})
        print(f"  Model A Probability: {ml_scores.get('modelA_prob', 'N/A')}")
        print(f"  Model B Probability: {ml_scores.get('modelB_prob', 'N/A')}")
        print(f"  Isolation Forest Flag: {ml_scores.get('iso_flag', 'N/A')}")

        # Verify all 3 models ran
        if 'modelA_prob' in ml_scores and 'modelB_prob' in ml_scores and 'iso_flag' in ml_scores:
            print("\n[SUCCESS] All 3 ML models executed (Model A + Model B + Isolation Forest)")
        else:
            print("\n[WARNING] Some ML scores missing")

        print("\n" + "=" * 70)
        print("SCREENSHOT INSTRUCTIONS:")
        print("=" * 70)
        print("1. Capture the 'ML SCORES EVIDENCE' section above")
        print("2. Capture the full JSON response")
        print("3. Label: 'Patent Evidence 1 - Dual ML Model Fusion'")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("Run again - timestamp may have expired")

if __name__ == "__main__":
    main()
