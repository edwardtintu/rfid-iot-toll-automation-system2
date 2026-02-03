import json
import os

# Load policy from file
policy_file = os.path.join(os.path.dirname(__file__), "trust_policy.json")
with open(policy_file) as f:
    POLICY = json.load(f)

def evaluate_trust(reader, violations):
    """
    Evaluate trust score based on violations and policy
    
    Args:
        reader: Reader object with current trust score
        violations: List of violation types
        
    Returns:
        tuple: (new_score, new_status)
    """
    score = reader["trust_score"]

    # Apply penalties for violations
    for v in violations:
        penalty = POLICY["penalties"].get(v, 0)
        score -= penalty

    # Apply reward for clean transaction (only if no violations)
    if not violations:
        score += POLICY["rewards"]["clean_transaction"]
    
    # Ensure score stays within bounds [0, 100]
    score = max(0, min(100, score))

    # Determine status based on thresholds
    if score <= POLICY["thresholds"]["suspended"]:
        status = "SUSPENDED"
    elif score <= POLICY["thresholds"]["degraded"]:
        status = "DEGRADED"
    else:
        status = "TRUSTED"

    return score, status