import sys
sys.path.append('/Users/hariharansundaramoorthy/HTMS_Project/backend')

# Test the detection logic with a sample transaction
from detection import run_detection

# Test transaction
test_transaction = {
    "amount": 120,
    "speed": 60,
    "inter_arrival": 5,
    "vehicle_type": "CAR",
    "last_seen": None  # No previous transaction
}

print("Testing detection system with a sample transaction:")
result = run_detection(test_transaction)

print(f"Result: {result}")
print(f"Flagged: {result['flagged']}")
print(f"Action: {result['action']}")
print(f"ML Scores: {result['ml_scores']}")
print("Model A is working and providing prediction probability!")