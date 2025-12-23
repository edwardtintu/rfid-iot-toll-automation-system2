import requests
import json

# Test the toll API to verify Model A is working with different inputs
BASE_URL = "http://127.0.0.1:8000"

print("Testing Model A with different transaction types...")

# Test with different card (to avoid duplicate detection)
test_transactions = [
    {"tagUID": "BE9E1E33", "speed": 60},  # BUS at normal speed
    {"tagUID": "9C981B6", "speed": 40},   # TRUCK at lower speed
]

for i, tx_data in enumerate(test_transactions):
    print(f"\nTest {i+1}: {tx_data}")
    response = requests.post(f"{BASE_URL}/api/toll", json=tx_data)
    result = response.json()
    
    if 'ml_scores' in result:
        print(f"  ModelA Prob: {result['ml_scores']['modelA_prob']}")
        print(f"  ModelB Prob: {result['ml_scores']['modelB_prob']}")
        print(f"  Action: {result['action']}")
        print(f"  Flagged: {result['flagged']}")
    else:
        print(f"  Error: {result}")