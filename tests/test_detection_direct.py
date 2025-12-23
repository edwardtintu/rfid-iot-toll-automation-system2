import sys, os
sys.path.append('/Users/hariharansundaramoorthy/HTMS_Project/backend')

# Change to the backend directory so it can find the models
os.chdir('/Users/hariharansundaramoorthy/HTMS_Project/backend')

# Test our detection function directly to verify Model A
from detection import run_detection

print("Testing Model A directly with different transaction patterns...")

# Test cases
test_cases = [
    {"amount": 120, "speed": 60, "inter_arrival": 5, "vehicle_type": "CAR", "last_seen": None},
    {"amount": 0.5, "speed": 5, "inter_arrival": 0.1, "vehicle_type": "CAR", "last_seen": None},  # Suspicious
    {"amount": 500, "speed": 150, "inter_arrival": 0.05, "vehicle_type": "CAR", "last_seen": None},  # Highly suspicious
    {"amount": 5.5, "speed": 65, "inter_arrival": 3, "vehicle_type": "CAR", "last_seen": None},  # Normal
]

for i, tx in enumerate(test_cases):
    print(f"\nTest {i+1}: {tx}")
    result = run_detection(tx)
    print(f"  ModelA Prob: {result['ml_scores']['modelA_prob']}")
    print(f"  ModelB Prob: {result['ml_scores']['modelB_prob']}")
    print(f"  Action: {result['action']}")
    print(f"  Flagged: {result['flagged']}")