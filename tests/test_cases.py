import pandas as pd
from datetime import datetime

def create_test_cases():
    """
    Create comprehensive test cases for HTMS project in tabular format
    """
    test_cases = [
        {
            "Test Case ID": "TC001",
            "Test Case Description": "Valid CAR transaction with sufficient balance",
            "Input": "tagUID: 5B88F75, vehicle_type: CAR, balance: 500, amount: 120, speed: 65",
            "Expected Output": "Decision: allow, new_balance: 380, blockchain: recorded",
            "Actual Result": "To be executed",
            "Status": "Pending",
            "Priority": "High"
        },
        {
            "Test Case ID": "TC002",
            "Test Case Description": "Valid TRUCK transaction with sufficient balance",
            "Input": "tagUID: 9C981B6, vehicle_type: TRUCK, balance: 1000, amount: 400, speed: 70",
            "Expected Output": "Decision: allow, new_balance: 600, blockchain: recorded",
            "Actual Result": "To be executed",
            "Status": "Pending",
            "Priority": "High"
        },
        {
            "Test Case ID": "TC003",
            "Test Case Description": "Valid BUS transaction with sufficient balance",
            "Input": "tagUID: BE9E1E33, vehicle_type: BUS, balance: 800, amount: 250, speed: 55",
            "Expected Output": "Decision: allow, new_balance: 550, blockchain: recorded",
            "Actual Result": "To be executed",
            "Status": "Pending",
            "Priority": "High"
        },
        {
            "Test Case ID": "TC004",
            "Test Case Description": "Insufficient balance transaction",
            "Input": "tagUID: A2E15F20, vehicle_type: CAR, balance: 80, amount: 120, speed: 60",
            "Expected Output": "Decision: block, reason: Insufficient balance, new_balance: 80",
            "Actual Result": "To be executed",
            "Status": "Pending",
            "Priority": "High"
        },
        {
            "Test Case ID": "TC005",
            "Test Case Description": "Fraudulent transaction detected by ModelB (high risk)",
            "Input": "tagUID: FRAUD001, vehicle_type: CAR, amount: 120, speed: 150, last_seen: recent",
            "Expected Output": "Decision: block, reason: High fraud probability (RF), blockchain: recorded",
            "Actual Result": "To be executed",
            "Status": "Pending",
            "Priority": "High"
        },
        {
            "Test Case ID": "TC006",
            "Test Case Description": "Duplicate scan within 1 minute",
            "Input": "tagUID: 5B88F75, vehicle_type: CAR, balance: 500, amount: 120, last_seen: 30s_ago",
            "Expected Output": "Decision: block, reason: Duplicate RFID scan within 1 minute",
            "Actual Result": "To be executed",
            "Status": "Pending",
            "Priority": "Medium"
        },
        {
            "Test Case ID": "TC007",
            "Test Case Description": "High toll amount for CAR vehicle type",
            "Input": "tagUID: CAR999, vehicle_type: CAR, amount: 500, speed: 60",
            "Expected Output": "Decision: block, reason: Car charged more than expected",
            "Actual Result": "To be executed",
            "Status": "Pending",
            "Priority": "Medium"
        },
        {
            "Test Case ID": "TC008",
            "Test Case Description": "Card lookup with valid UID",
            "Input": "tagUID: 9C981B6",
            "Expected Output": "Returns card details with owner_name, vehicle_number, balance, tariff_amount",
            "Actual Result": "To be executed",
            "Status": "Pending",
            "Priority": "Medium"
        },
        {
            "Test Case ID": "TC009",
            "Test Case Description": "Card lookup with invalid UID",
            "Input": "tagUID: INVALID999",
            "Expected Output": "Error: Card not found, HTTP 404",
            "Actual Result": "To be executed",
            "Status": "Pending",
            "Priority": "Low"
        },
        {
            "Test Case ID": "TC010",
            "Test Case Description": "Abnormally high toll amount (Rule-based detection)",
            "Input": "tagUID: TEST999, amount: 6000, vehicle_type: TRUCK, speed: 60",
            "Expected Output": "Decision: block, reason: Abnormally high toll, blockchain: recorded",
            "Actual Result": "To be executed",
            "Status": "Pending",
            "Priority": "High"
        }
    ]
    
    # Create DataFrame
    df = pd.DataFrame(test_cases)
    
    # Print the table in a formatted way
    print("="*150)
    print("HTMS PROJECT - TEST CASE SPECIFICATION")
    print("="*150)
    
    # Print column headers
    print(f"{'Test Case ID':<12} {'Test Case Description':<50} {'Priority':<8} {'Status':<8} {'Expected Output':<60}")
    print("-"*150)
    
    # Print each test case
    for _, row in df.iterrows():
        print(f"{row['Test Case ID']:<12} {row['Test Case Description']:<50} {row['Priority']:<8} {row['Status']:<8} {row['Expected Output'][:58]:<60}")
    
    print("="*150)
    
    # Print the full table using pandas for better readability
    print("\nDETAILED TEST CASE TABLE:")
    print("-" * 80)
    print(df.to_string(index=False))
    
    # Save to CSV for documentation purposes
    df.to_csv('htms_test_cases.csv', index=False)
    print(f"\n✅ Test cases saved to 'htms_test_cases.csv'")
    
    # Summary statistics
    print(f"\n📊 TEST CASE SUMMARY:")
    print(f"   • Total Test Cases: {len(df)}")
    print(f"   • High Priority: {(df['Priority'] == 'High').sum()}")
    print(f"   • Medium Priority: {(df['Priority'] == 'Medium').sum()}")
    print(f"   • Low Priority: {(df['Priority'] == 'Low').sum()}")
    print(f"   • Test Cases by Category:")
    print(f"     - Normal Operations: {(df['Test Case Description'].str.contains('Valid|Card lookup', case=False)).sum()}")
    print(f"     - Fraud Detection: {(df['Test Case Description'].str.contains('Fraud|Duplicate|amount|Insufficient', case=False)).sum()}")
    print(f"     - Error Handling: {(df['Test Case Description'].str.contains('invalid|Error', case=False)).sum()}")
    
    return df

def run_specific_test_case(test_case_id):
    """
    Function to simulate running a specific test case
    """
    test_cases = {
        "TC001": {
            "description": "Valid CAR transaction with sufficient balance",
            "input": {"tagUID": "5B88F75", "vehicle_type": "CAR", "balance": 500, "amount": 120, "speed": 65},
            "expected": {"decision": "allow", "new_balance": 380, "blockchain": "recorded"}
        },
        "TC002": {
            "description": "Valid TRUCK transaction with sufficient balance", 
            "input": {"tagUID": "9C981B6", "vehicle_type": "TRUCK", "balance": 1000, "amount": 400, "speed": 70},
            "expected": {"decision": "allow", "new_balance": 600, "blockchain": "recorded"}
        },
        "TC004": {
            "description": "Insufficient balance transaction",
            "input": {"tagUID": "A2E15F20", "vehicle_type": "CAR", "balance": 80, "amount": 120, "speed": 60},
            "expected": {"decision": "block", "reason": "Insufficient balance", "new_balance": 80}
        }
    }
    
    if test_case_id in test_cases:
        tc = test_cases[test_case_id]
        print(f"\n🔬 RUNNING TEST CASE {test_case_id}: {tc['description']}")
        print(f"Input: {tc['input']}")
        print(f"Expected: {tc['expected']}")
        print(f"Status: PASSED (simulated)")
    else:
        print(f"Test case {test_case_id} not found")

if __name__ == "__main__":
    print("🧪 HTMS PROJECT TEST CASE GENERATION")
    df = create_test_cases()
    
    print("\n" + "="*50)
    print("SAMPLE TEST CASE EXECUTION")
    print("="*50)
    
    # Example of running a specific test case
    run_specific_test_case("TC001")
    run_specific_test_case("TC002")
    run_specific_test_case("TC004")
    
    print(f"\n📋 To execute all test cases, run each API endpoint with the specified inputs")
    print(f"   and verify against the expected outputs.")